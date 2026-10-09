from django.core.management.base import BaseCommand

from store.models import Item

# (slug, name, description, slot, rarity, price, min_level, art)
CATALOGUE = [
    ("starter-cap", "Starter Cap", "Everybody starts somewhere.", "hat", "common", 0, 1, "🧢"),
    ("party-hat", "Party Hat", "Every accepted report is a celebration.", "hat", "common", 40, 1, "🥳"),
    ("detective-hat", "Detective Hat", "For sleuthing through stack traces.", "hat", "rare", 150, 2, "🕵️"),
    ("wizard-hat", "Wizard Hat", "Sudo, but magic.", "hat", "epic", 500, 4, "🧙"),
    ("golden-crown", "Golden Crown", "For the top of the leaderboard.", "hat", "legendary", 1500, 6, "👑"),
    ("cool-shades", "Cool Shades", "Too cool to log in with 'admin'.", "face", "common", 60, 1, "😎"),
    ("nerd-glasses", "Nerd Glasses", "Reads the RFC for fun.", "face", "common", 80, 1, "🤓"),
    ("hacker-mask", "Hacker Mask", "Strictly for the good guys.", "face", "rare", 250, 3, "🥷"),
    ("lab-coat", "Lab Coat", "Safety first, exploits second.", "body", "rare", 200, 2, "🥼"),
    ("space-suit", "Space Suit", "Reaching new attack surfaces.", "body", "epic", 600, 5, "🧑‍🚀"),
    ("pet-bug", "Pet Bug", "Your first bug, domesticated.", "pet", "common", 100, 1, "🐞"),
    ("pet-owl", "Wise Owl", "Has seen every CVE.", "pet", "rare", 300, 3, "🦉"),
    ("pet-dragon", "Tiny Dragon", "Breathes fire on legacy code.", "pet", "legendary", 1200, 6, "🐉"),
    ("bg-matrix", "Matrix Rain", "Green characters falling.", "background", "rare", 180, 2, "🟩"),
    ("bg-galaxy", "Galaxy", "Infinite scope.", "background", "epic", 450, 4, "🌌"),
]


class Command(BaseCommand):
    help = "Create or update the starter store catalogue (idempotent; keeps prices you edited)."

    def handle(self, *args, **options):
        created = 0
        for order, (slug, name, description, slot, rarity, price, min_level, art) in enumerate(CATALOGUE):
            _, was_created = Item.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name=name, description=description, slot=slot, rarity=rarity,
                    price=price, min_level=min_level, art=art, sort_order=order,
                ),
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(
            f"Store catalogue ready: {created} item(s) added, {len(CATALOGUE) - created} already there."
        ))
