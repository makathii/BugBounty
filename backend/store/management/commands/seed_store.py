from django.core.management.base import BaseCommand

from store.models import Item

# (slug, name, description, slot, rarity, price, min_level, art[, unlock_badge])
# Items with an unlock_badge and price 0 are rewards: they arrive when the badge is earned.
# New rows only: re-running never changes prices or text you edited in the admin.
CATALOGUE = [
    # --- hats ---
    ("starter-cap", "Starter Cap", "Everybody starts somewhere.", "hat", "common", 0, 1, "🧢"),
    ("party-hat", "Party Hat", "Every accepted report is a celebration.", "hat", "common", 40, 1, "🥳"),
    ("cowboy-hat", "Cowboy Hat", "Rounding up wild bugs.", "hat", "common", 70, 1, "🤠"),
    ("top-hat", "Top Hat", "Very formal disclosure.", "hat", "rare", 160, 2, "🎩"),
    ("detective-hat", "Detective Hat", "For sleuthing through stack traces.", "hat", "rare", 150, 2, "🕵️"),
    ("graduation-cap", "Graduation Cap", "Honours in input validation.", "hat", "rare", 220, 3, "🎓"),
    ("wizard-hat", "Wizard Hat", "Sudo, but magic.", "hat", "epic", 500, 4, "🧙"),
    ("golden-crown", "Golden Crown", "For the top of the leaderboard.", "hat", "legendary", 1500, 6, "👑"),
    # --- faces ---
    ("cool-shades", "Cool Shades", "Too cool to log in with 'admin'.", "face", "common", 60, 1, "😎"),
    ("nerd-glasses", "Nerd Glasses", "Reads the RFC for fun.", "face", "common", 80, 1, "🤓"),
    ("monocle", "Monocle", "Inspecting every header.", "face", "common", 90, 1, "🧐"),
    ("party-face", "Party Face", "Found one. Celebrating.", "face", "rare", 130, 2, "🥸"),
    ("hacker-mask", "Hacker Mask", "Strictly for the good guys.", "face", "rare", 250, 3, "🥷"),
    ("robot-face", "Robot Face", "Fuzzes in its sleep.", "face", "epic", 420, 4, "🤖"),
    ("alien-face", "Alien Face", "Not from this attack surface.", "face", "epic", 520, 5, "👽"),
    # --- bodies ---
    ("hoodie", "Hacker Hoodie", "Obligatory.", "body", "common", 90, 1, "🧥"),
    ("lab-coat", "Lab Coat", "Safety first, exploits second.", "body", "rare", 200, 2, "🥼"),
    ("superhero-cape", "Super Cape", "With great scope comes great responsibility.", "body", "rare", 280, 3, "🦸"),
    ("armor", "Knight's Armour", "Hardened against injection.", "body", "epic", 560, 4, "🛡️"),
    ("space-suit", "Space Suit", "Reaching new attack surfaces.", "body", "epic", 600, 5, "🧑‍🚀"),
    # --- pets ---
    ("pet-bug", "Pet Bug", "Your first bug, domesticated.", "pet", "common", 100, 1, "🐞"),
    ("pet-cat", "Debug Cat", "Sits on the keyboard. Finds the bug.", "pet", "common", 120, 1, "🐈"),
    ("pet-crab", "Rustacean", "Memory safe, mostly.", "pet", "rare", 240, 2, "🦀"),
    ("pet-owl", "Wise Owl", "Has seen every CVE.", "pet", "rare", 300, 3, "🦉"),
    ("pet-fox", "Fuzzer Fox", "Quick, brown and mutating.", "pet", "rare", 340, 3, "🦊"),
    ("pet-octopus", "Octopus", "Eight arms, eight terminals.", "pet", "epic", 480, 4, "🐙"),
    ("pet-dragon", "Tiny Dragon", "Breathes fire on legacy code.", "pet", "legendary", 1200, 6, "🐉"),
    ("pet-unicorn", "Unicorn", "Rare as a zero-day.", "pet", "legendary", 1800, 7, "🦄"),
    # --- backgrounds ---
    ("bg-sunset", "Sunset", "Disclosed just before the deadline.", "background", "common", 100, 1, "🌇"),
    ("bg-matrix", "Matrix Rain", "Green characters falling.", "background", "rare", 180, 2, "🟩"),
    ("bg-ocean", "Deep Ocean", "Diving into the deep web.", "background", "rare", 230, 2, "🌊"),
    ("bg-galaxy", "Galaxy", "Infinite scope.", "background", "epic", 450, 4, "🌌"),
    ("bg-volcano", "Volcano", "A critical finding erupts.", "background", "epic", 540, 5, "🌋"),
    # --- badge rewards: free, added when the badge is earned ---
    ("reward-bandage", "Battle Plaster", "Your first bug left a mark.", "face", "rare", 0, 1, "🩹", "first_blood"),
    ("reward-explosion", "Blast Zone", "A critical finding, still smoking.", "background", "epic", 0, 1, "💥", "critical_thinker"),
    ("reward-hardhat", "Hard Hat", "For heavy lifting.", "hat", "epic", 0, 1, "⛑️", "heavy_hitter"),
    ("reward-beetle", "Beetle Buddy", "Collects bugs, so you don't have to.", "pet", "epic", 0, 1, "🪲", "collector"),
    ("reward-trophy", "Trophy Room", "Twenty-five accepted reports.", "background", "legendary", 0, 1, "🏆", "hoarder"),
    ("reward-backpack", "Explorer Pack", "Three programs, three stamps.", "body", "epic", 0, 1, "🎒", "globetrotter"),
    ("reward-star-eyes", "Star Eyes", "A report so good the triager noticed.", "face", "epic", 0, 1, "🤩", "standout"),
    ("reward-halo", "Clean Halo", "Five in a row, no misses.", "hat", "legendary", 0, 1, "😇", "clean_streak"),
]


class Command(BaseCommand):
    help = "Create or update the starter store catalogue (idempotent; keeps prices you edited)."

    def handle(self, *args, **options):
        created = 0
        for order, (slug, name, description, slot, rarity, price, min_level, art, *badge) in enumerate(CATALOGUE):
            _, was_created = Item.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name=name, description=description, slot=slot, rarity=rarity,
                    price=price, min_level=min_level, art=art, sort_order=order,
                    unlock_badge=badge[0] if badge else "",
                ),
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(
            f"Store catalogue ready: {created} item(s) added, {len(CATALOGUE) - created} already there."
        ))
