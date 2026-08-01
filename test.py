def test_postgres_connection():
    """Test PostgreSQL connection using simple socket check."""
    import socket
    
    try:
        # Test if PostgreSQL port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', 5433))
        sock.close()
        
        if result == 0:
            print("✓ PostgreSQL is accepting connections on port 5432!")
            return True
        else:
            print("✗ PostgreSQL port is not accessible")
            return False
            
    except Exception as e:
        print(f"✗ Could not test PostgreSQL: {e}")
        return False

postgres_available = test_postgres_connection()

if postgres_available:
    print("\n  Database Connection Details:")
    print("• Host: localhost")
    print("• Port: 5432") 
    print("• Database: rag_db")
    print("• Username: rag_user")
    print("• Password: rag_password")
    
    print("\n  Recommended GUI Tools:")
    print("• DBeaver (Free): https://dbeaver.io/download/")
    print("• pgAdmin: https://www.pgadmin.org/download/")


try:
    import psycopg
    
    conn = psycopg.connect(
        host="localhost",
        port=5433,
        dbname="rag_db", 
        user="rag_user",
        password="rag_password"
    )
    
    print("✓ PostgreSQL connected")
    cursor = conn.cursor()
    
except ImportError:
    print("⚠ psycopg2 not installed - basic connection only")
    exit()
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    exit()


cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")

all_tables = cursor.fetchall()

app_tables = []
airflow_tables = []

for (table_name,) in all_tables:
    if table_name in ['papers', 'users', 'embeddings']:
        app_tables.append(table_name)
    else:
        airflow_tables.append(table_name)

print(f"Found {len(all_tables)} total tables")
print(f"Application tables: {len(app_tables)}")
print(f"Airflow tables: {len(airflow_tables)}")

for table in app_tables:
    print(f"  • {table}")

if not app_tables:
    print("  No application tables yet (expected in Week 1)")
    
cursor.close()
conn.close()
