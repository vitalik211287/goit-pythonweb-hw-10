from datetime import date, timedelta

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas import ContactCreate, ContactUpdate


class ContactRepository:
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_contacts(
        self,
        skip: int,
        limit: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        user: User | None = None,
    ):
        stmt = select(Contact)

        filters = []

        if user:
            filters.append(Contact.user_id == user.id)

        if first_name:
            filters.append(Contact.first_name.ilike(f"%{first_name}%"))

        if last_name:
            filters.append(Contact.last_name.ilike(f"%{last_name}%"))

        if email:
            filters.append(Contact.email.ilike(f"%{email}%"))

        if filters:
            stmt = stmt.where(*filters)

        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_contact_by_id(self, contact_id: int, user: User):
        stmt = select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user.id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_contact(self, body: ContactCreate, user: User):
        contact = Contact(
            **body.model_dump(),
            user_id=user.id,
        )
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def update_contact(
        self,
        contact_id: int,
        body: ContactUpdate,
        user: User,
    ):
        contact = await self.get_contact_by_id(contact_id, user)

        if contact:
            for key, value in body.model_dump().items():
                setattr(contact, key, value)

            await self.db.commit()
            await self.db.refresh(contact)

        return contact

    async def delete_contact(self, contact_id: int, user: User):
        contact = await self.get_contact_by_id(contact_id, user)

        if contact:
            await self.db.delete(contact)
            await self.db.commit()

        return contact

    async def get_upcoming_birthdays(self, user: User):
        today = date.today()
        next_week = today + timedelta(days=7)

        stmt = select(Contact).where(Contact.user_id == user.id)

        result = await self.db.execute(stmt)
        contacts = result.scalars().all()

        upcoming = []

        for contact in contacts:
            birthday_this_year = contact.birthday.replace(year=today.year)

            if birthday_this_year < today:
                birthday_this_year = birthday_this_year.replace(year=today.year + 1)

            if today <= birthday_this_year <= next_week:
                upcoming.append(contact)

        return upcoming