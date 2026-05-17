from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.repository.contacts import ContactRepository
from src.schemas import ContactCreate, ContactUpdate


class ContactService:
    def __init__(self, db: AsyncSession):
        self.repository = ContactRepository(db)

    async def get_contacts(
        self,
        skip: int,
        limit: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        user: User | None = None,
    ):
        return await self.repository.get_contacts(
            skip,
            limit,
            first_name,
            last_name,
            email,
            user,
        )

    async def get_contact(self, contact_id: int, user: User):
        return await self.repository.get_contact_by_id(contact_id, user)

    async def create_contact(self, body: ContactCreate, user: User):
        return await self.repository.create_contact(body, user)

    async def update_contact(
        self,
        contact_id: int,
        body: ContactUpdate,
        user: User,
    ):
        return await self.repository.update_contact(contact_id, body, user)

    async def delete_contact(self, contact_id: int, user: User):
        return await self.repository.delete_contact(contact_id, user)

    async def get_upcoming_birthdays(self, user: User):
        return await self.repository.get_upcoming_birthdays(user)