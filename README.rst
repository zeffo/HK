*****
HK-69
*****

Multipurpose discord bot for my friends and I

*********
Dev setup
*********

Install dependencies with Poetry:
::
  poetry install


Create environment variable ``DATABASE_URL`` for the local PostgreSQL database. (a .env file works too)

Set up the database and generate the Prisma client with
::
  prisma db push

*****************
Making migrations
*****************

In case you need to change the structure of the database, modify the ``schema.prisma`` file accordingly, then make a
new migration with the command
::
  prisma migrate dev

When prompted, enter a name for the migration, and commit the generated migration files to source control.
Then, regenerate the Prisma client
::
  prisma generate 