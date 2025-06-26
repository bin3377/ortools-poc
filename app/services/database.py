import os

from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv()

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("MONGODB_DATABASE_NAME", "scheduler")
DIRECTION_CACHE_TTL_SECONDS = int(
    os.getenv("DIRECTION_CACHE_TTL_SECONDS", "3600")
)  # Default: 1 hour


class Database:
    client: AsyncMongoClient = None
    database = None


database = Database()


async def get_database() -> AsyncMongoClient:
    return database.database


async def connect_to_mongo():
    """Create database connection"""

    database.client = AsyncMongoClient(MONGODB_URI)
    database.database = database.client[DATABASE_NAME]

    # Test the connection
    try:
        await database.client.admin.command("ping")
        print("Successfully connected to MongoDB")

        # Create indexes for directions collection
        await setup_indexes()

    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")


async def setup_indexes():
    """Setup extra indexes for collections"""
    try:
        directions_collection = database.database["directions"]

        # Create TTL index on created_at field (documents expire after TTL_SECONDS)
        await directions_collection.create_index(
            [("created_at", 1)],
            expireAfterSeconds=DIRECTION_CACHE_TTL_SECONDS,
            background=True,
        )

        # Create unique index on key field for efficient lookups
        await directions_collection.create_index(
            [("key", 1)], unique=True, background=True
        )

        print(
            f"Direction collection indexes created successfully (TTL: {DIRECTION_CACHE_TTL_SECONDS}s)"
        )

        program_collection = database.database["programs"]

        # Create unique index on id field for efficient lookups
        await program_collection.create_index([("id", 1)], unique=True, background=True)

        # Create unique index on name field for efficient lookups
        await program_collection.create_index(
            [("name", 1)], unique=True, background=True
        )

        print("Program collection indexes created successfully")

        task_collection = database.database["tasks"]

        # Create unique index on id field for efficient lookups
        await task_collection.create_index([("id", 1)], unique=True, background=True)

        print("Task collection indexes created successfully")

    except Exception as e:
        print(f"Error creating direction indexes: {e}")


async def close_mongo_connection():
    """Close database connection"""
    if database.client:
        await database.client.close()
        print("Disconnected from MongoDB")
