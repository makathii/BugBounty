from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import is_admin_or_triager
from core.tasks import enqueue_after_commit

from ..models import Comment
from ..serializers import CommentSerializer, build_comment_tree
from ..services import ActivityLogger
from ..tasks import send_comment_notification

MAX_REPLY_DEPTH = 5


def visible_comments(report, request):
    """Comments on ``report`` that ``request.user`` may see (internal notes: triage staff only)."""
    qs = report.comments.select_related("author").order_by("created_at", "id")
    if not is_admin_or_triager(request):
        qs = qs.filter(is_internal=False)
    return qs


class CommentActionsMixin:
    """Threaded comments for BugReportViewSet.

    GET/POST   /reports/{id}/comments/                  thread (nested) / new comment or reply
    PATCH/DEL  /reports/{id}/comments/{comment_id}/     edit own / delete own (staff: any)
    POST       /reports/{id}/comment/                   legacy alias for the POST above
    """

    def _comment_context(self):
        return {"request": self.request}

    @action(detail=True, methods=["get", "post"], url_path="comments",
            permission_classes=[IsAuthenticated])
    def comments(self, request, pk=None):
        report = self.get_object()
        if request.method == "GET":
            tree = build_comment_tree(
                list(visible_comments(report, request)), self._comment_context(),
            )
            return Response(tree)
        return self._create_comment(request, report)

    @action(detail=True, methods=["post"], url_path="comment",
            permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        return self._create_comment(request, self.get_object())

    @action(detail=True, methods=["patch", "delete"],
            url_path=r"comments/(?P<comment_id>\d+)",
            permission_classes=[IsAuthenticated])
    def comment_detail(self, request, pk=None, comment_id=None):
        report = self.get_object()
        comment = get_object_or_404(visible_comments(report, request), pk=comment_id)
        if comment.is_deleted:
            return Response({"detail": "Comment was deleted."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "DELETE":
            if comment.author_id != request.user.id and not is_admin_or_triager(request):
                return Response(
                    {"detail": "You can only delete your own comments."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            comment.soft_delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if comment.author_id != request.user.id:
            return Response(
                {"detail": "You can only edit your own comments."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CommentSerializer(
            comment, data={"text": request.data.get("text", "")},
            partial=True, context=self._comment_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(edited_at=timezone.now())
        return Response(serializer.data)

    def _create_comment(self, request, report):
        staff = is_admin_or_triager(request)
        is_internal = _as_bool(request.data.get("is_internal"))
        if is_internal and not staff:
            return Response(
                {"detail": "Only Triagers and Admins can post internal notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        parent = None
        parent_id = request.data.get("parent")
        if parent_id not in (None, ""):
            try:
                parent = visible_comments(report, request).filter(pk=int(parent_id)).first()
            except (TypeError, ValueError):
                parent = None
            if parent is None:
                return Response(
                    {"parent": "Parent comment not found on this report."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if parent.depth() + 1 > MAX_REPLY_DEPTH:
                return Response(
                    {"parent": f"Replies can be nested at most {MAX_REPLY_DEPTH} levels deep."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # A reply inside an internal thread can never become public.
            is_internal = is_internal or parent.is_internal

        serializer = CommentSerializer(
            data={"text": request.data.get("text", "")}, context=self._comment_context(),
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(
            author=request.user, report=report, parent=parent, is_internal=is_internal,
        )
        ActivityLogger.log_comment(report, request.user, comment)
        try:
            enqueue_after_commit(send_comment_notification, comment.id)
        except Exception:  # never fail a comment because of mail
            pass
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")
