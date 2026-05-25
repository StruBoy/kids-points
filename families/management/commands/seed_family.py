from django.core.management.base import BaseCommand
from django.db import transaction

from families.models import User
from store.models import ItemType, StoreItem


class Command(BaseCommand):
    help = "Seed one demo family (2 parents, 2 kids) and a few store items."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing users and store items before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            self.stdout.write("Resetting users and store items...")
            User.objects.all().delete()
            StoreItem.objects.all().delete()

        if User.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Users already exist; pass --reset to wipe and reseed."
            ))
            return

        User.objects.create_parent(
            username="mom", name="Mom", password="password"
        )
        User.objects.create_parent(
            username="dad", name="Dad", password="password"
        )
        User.objects.create_kid(name="Alex", pin="1234")
        User.objects.create_kid(name="Sam", pin="5678")

        StoreItem.objects.create(
            name="30 min screen time",
            description="Half an hour of video games or a show.",
            cost=10,
            type=ItemType.REPEATABLE,
        )
        StoreItem.objects.create(
            name="Pick the dinner menu",
            description="You choose what's for dinner tonight.",
            cost=20,
            type=ItemType.REPEATABLE,
        )
        StoreItem.objects.create(
            name="Trip to the bookstore",
            description="One book of your choice, up to $15.",
            cost=50,
            type=ItemType.LIMITED,
            stock_remaining=2,
        )
        StoreItem.objects.create(
            name="Lego set",
            description="A small Lego set from the wishlist.",
            cost=100,
            type=ItemType.LIMITED,
            stock_remaining=1,
        )

        self.stdout.write(self.style.SUCCESS(
            "Seeded: 2 parents (mom/dad, password=password), "
            "2 kids (Alex pin=1234, Sam pin=5678), 4 store items."
        ))
