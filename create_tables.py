from utils.db_handler import init_postgres_db

def create_tables():
    try:
        init_postgres_db()
        print("PostgreSQL machine tables created successfully.")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    create_tables()
