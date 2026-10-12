import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CommentThread from './CommentThread';
import { reportAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
    reportAPI: { getComments: jest.fn(), addComment: jest.fn(), editComment: jest.fn(), deleteComment: jest.fn() },
}));

const comment = (id, text, extra = {}) => ({
    id, text, author: 'parsa', author_loadout: {}, created_at: '2026-10-09T10:00:00Z', edited_at: null,
    is_internal: false, is_deleted: false, can_edit: false, can_delete: false, parent: null, replies: [], ...extra,
});
const mockThread = (...tree) => reportAPI.getComments.mockResolvedValue({ data: tree });
const row = (text) => screen.getByText(text).closest('.ui-comment');

beforeEach(() => {
    jest.resetAllMocks();
    window.confirm = jest.fn(() => true);
    window.alert = jest.fn();
});

describe('CommentThread', () => {
    test('shows an empty state', async () => {
        mockThread();
        render(<CommentThread reportId="5" />);
        expect(await screen.findByText(/No comments yet/)).toBeInTheDocument();
    });

    test('renders replies nested under their parent', async () => {
        mockThread(comment(1, 'root', { replies: [comment(2, 'child', { author: 'triager' })] }));
        render(<CommentThread reportId="5" />);
        const child = await screen.findByText('child');
        const replies = child.closest('.ui-comment-replies');
        expect(replies).not.toBeNull();
        expect(replies.parentElement).toBe(row('root'));
    });

    test('draws the author\'s character', async () => {
        mockThread(comment(1, 'hi', { author_loadout: { hat: { slug: 'cap', name: 'Cap', art: '🧢', slot: 'hat' } } }));
        const { container } = render(<CommentThread reportId="5" />);
        await screen.findByText('hi');
        expect(container.querySelector('.ui-character-hat')).toHaveTextContent('🧢');
    });

    test('internal notes are badged, and only moderators can write them', async () => {
        mockThread(comment(1, 'secret', { is_internal: true, author: 'triager' }));
        const { unmount } = render(<CommentThread reportId="5" canModerate={false} />);
        expect(await screen.findByText('Internal')).toBeInTheDocument();
        expect(screen.queryByLabelText(/Internal note/)).toBeNull();
        unmount();
        mockThread();
        render(<CommentThread reportId="5" canModerate />);
        expect(await screen.findByLabelText(/Internal note/)).toBeInTheDocument();
    });

    test('posting a comment sends it, clears the box and reloads the thread', async () => {
        mockThread();
        reportAPI.addComment.mockResolvedValue({});
        render(<CommentThread reportId="5" />);
        await screen.findByText(/No comments yet/);
        const submit = screen.getByRole('button', { name: 'Add Comment' });
        expect(submit).toBeDisabled();
        userEvent.type(screen.getByPlaceholderText('Add a comment...'), 'First!');
        mockThread(comment(1, 'First!'));
        userEvent.click(submit);
        expect(await screen.findByText('First!', { selector: 'p' })).toBeInTheDocument();
        expect(reportAPI.addComment).toHaveBeenCalledWith('5', { text: 'First!', is_internal: false, parent: null });
        expect(screen.getByPlaceholderText('Add a comment...')).toHaveValue('');
    });

    test('a moderator can post an internal note', async () => {
        mockThread();
        reportAPI.addComment.mockResolvedValue({});
        render(<CommentThread reportId="5" canModerate />);
        await screen.findByText(/No comments yet/);
        userEvent.type(screen.getByPlaceholderText('Add a comment...'), 'for staff');
        userEvent.click(screen.getByLabelText(/Internal note/));
        userEvent.click(screen.getByRole('button', { name: 'Add Comment' }));
        await waitFor(() => expect(reportAPI.addComment).toHaveBeenCalledWith(
            '5', { text: 'for staff', is_internal: true, parent: null }));
    });

    test('replying sends the parent id; replies to internal notes cannot be made public', async () => {
        mockThread(comment(9, 'note', { is_internal: true }));
        reportAPI.addComment.mockResolvedValue({});
        render(<CommentThread reportId="5" canModerate />);
        await screen.findByText('note');
        userEvent.click(within(row('note')).getByRole('button', { name: 'Reply' }));
        const form = row('note').querySelector('.ui-comment-form');
        expect(within(form).queryByLabelText(/Internal note/)).toBeNull(); // forced internal, no toggle
        userEvent.type(within(form).getByRole('textbox'), 'ack');
        userEvent.click(within(form).getByRole('button', { name: 'Reply' }));
        await waitFor(() => expect(reportAPI.addComment).toHaveBeenCalledWith(
            '5', { text: 'ack', is_internal: true, parent: 9 }));
    });

    test('shows the server error and keeps the draft when posting fails', async () => {
        mockThread();
        reportAPI.addComment.mockRejectedValue({ response: { data: { text: ['Comment cannot be empty.'] } } });
        render(<CommentThread reportId="5" />);
        await screen.findByText(/No comments yet/);
        userEvent.type(screen.getByPlaceholderText('Add a comment...'), 'x');
        userEvent.click(screen.getByRole('button', { name: 'Add Comment' }));
        expect(await screen.findByText('Comment cannot be empty.')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Add a comment...')).toHaveValue('x');
    });

    test('edit and delete only appear when the server allows them', async () => {
        mockThread(comment(1, 'mine', { can_edit: true, can_delete: true }), comment(2, 'theirs'));
        render(<CommentThread reportId="5" />);
        await screen.findByText('mine');
        expect(within(row('mine')).getByRole('button', { name: 'Edit' })).toBeInTheDocument();
        expect(within(row('mine')).getByRole('button', { name: 'Delete' })).toBeInTheDocument();
        expect(within(row('theirs')).queryByRole('button', { name: 'Edit' })).toBeNull();
        expect(within(row('theirs')).queryByRole('button', { name: 'Delete' })).toBeNull();
    });

    test('editing saves the new text', async () => {
        mockThread(comment(1, 'typo', { can_edit: true }));
        reportAPI.editComment.mockResolvedValue({});
        render(<CommentThread reportId="5" />);
        await screen.findByText('typo');
        userEvent.click(screen.getByRole('button', { name: 'Edit' }));
        const box = screen.getByDisplayValue('typo');
        userEvent.clear(box);
        userEvent.type(box, 'fixed');
        userEvent.click(screen.getByRole('button', { name: 'Save' }));
        await waitFor(() => expect(reportAPI.editComment).toHaveBeenCalledWith('5', 1, { text: 'fixed' }));
    });

    test('deleting asks first, and "cancel" deletes nothing', async () => {
        mockThread(comment(1, 'bye', { can_delete: true }));
        reportAPI.deleteComment.mockResolvedValue({});
        render(<CommentThread reportId="5" />);
        await screen.findByText('bye');
        window.confirm.mockReturnValueOnce(false);
        userEvent.click(screen.getByRole('button', { name: 'Delete' }));
        expect(reportAPI.deleteComment).not.toHaveBeenCalled();
        userEvent.click(screen.getByRole('button', { name: 'Delete' }));
        await waitFor(() => expect(reportAPI.deleteComment).toHaveBeenCalledWith('5', 1));
    });

    test('a deleted comment keeps its place with a placeholder and its replies', async () => {
        mockThread(comment(1, '', { is_deleted: true, replies: [comment(2, 'still here')] }));
        render(<CommentThread reportId="5" />);
        expect(await screen.findByText('[comment deleted]')).toBeInTheDocument();
        expect(screen.getByText('still here')).toBeInTheDocument();
        expect(within(row('[comment deleted]')).queryByRole('button', { name: 'Edit' })).toBeNull();
    });

    test('shows "(edited)" on edited comments', async () => {
        mockThread(comment(1, 'x', { edited_at: '2026-10-09T11:00:00Z' }));
        render(<CommentThread reportId="5" />);
        expect(await screen.findByText(/\(edited\)/)).toBeInTheDocument();
    });

    test('tells the parent when the thread changes (to refresh the activity log)', async () => {
        mockThread();
        reportAPI.addComment.mockResolvedValue({});
        const onChange = jest.fn();
        render(<CommentThread reportId="5" onChange={onChange} />);
        await screen.findByText(/No comments yet/);
        userEvent.type(screen.getByPlaceholderText('Add a comment...'), 'hi');
        userEvent.click(screen.getByRole('button', { name: 'Add Comment' }));
        await waitFor(() => expect(onChange).toHaveBeenCalled());
    });

    test('shows an error when the thread cannot be loaded', async () => {
        reportAPI.getComments.mockRejectedValue({ response: { data: { detail: 'Not found.' } } });
        render(<CommentThread reportId="5" />);
        expect(await screen.findByText('Not found.')).toBeInTheDocument();
    });
});
