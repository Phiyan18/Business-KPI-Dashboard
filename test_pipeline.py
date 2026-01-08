"""
Test Script for Business KPI Pipeline
Runs comprehensive tests to verify all components
"""
import sys
import yaml
from pathlib import Path

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def test_python_packages():
    """Test if all required packages are installed"""
    print_header("Testing Python Packages")
    
    required_packages = [
        'pandas', 'numpy', 'sqlalchemy', 'psycopg2', 
        'yaml', 'requests', 'schedule'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Install missing packages: pip install {' '.join(missing)}")
        return False
    return True

def test_config_file():
    """Test if config file exists and is valid"""
    print_header("Testing Configuration File")
    
    config_path = Path("config/config.yaml")
    
    if not config_path.exists():
        print("❌ config/config.yaml not found")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print("✅ config.yaml found and valid")
        
        # Check required keys
        required_keys = ['database', 'data_sources', 'quality_thresholds']
        for key in required_keys:
            if key in config:
                print(f"✅ {key} section exists")
            else:
                print(f"❌ {key} section missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {str(e)}")
        return False

def test_database_connection():
    """Test database connection"""
    print_header("Testing Database Connection")
    
    try:
        from database import DatabaseManager
        
        db = DatabaseManager()
        print("✅ Database connection successful")
        
        # Test simple query
        result = db.query_to_dataframe("SELECT 1 as test")
        if result is not None and len(result) > 0:
            print("✅ Database query successful")
        else:
            print("⚠️  Query returned no results")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print("\n💡 Troubleshooting:")
        print("   1. Check database is running")
        print("   2. Verify credentials in config.yaml")
        print("   3. Check firewall/network settings")
        return False

def test_directory_structure():
    """Test if directory structure exists"""
    print_header("Testing Directory Structure")
    
    required_dirs = [
        'data/raw',
        'data/processed',
        'data/logs',
        'config',
        'sql',
        'src'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} - NOT FOUND")
            all_exist = False
            # Try to create it
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"   → Created {dir_path}")
            except Exception as e:
                print(f"   → Failed to create: {e}")
    
    return all_exist

def test_data_files():
    """Test if data files exist"""
    print_header("Testing Data Files")
    
    data_files = [
        'data/raw/sales_data.csv',
        'data/raw/customer_data.csv',
        'data/raw/product_data.csv'
    ]
    
    files_exist = 0
    for file_path in data_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
            files_exist += 1
        else:
            print(f"⚠️  {file_path} - NOT FOUND")
    
    if files_exist == 0:
        print("\n💡 Generate sample data: python src/main.py --generate-data")
        return False
    elif files_exist < 3:
        print("\n⚠️  Some data files missing")
        return False
    
    return True

def test_module_imports():
    """Test if custom modules can be imported"""
    print_header("Testing Custom Modules")
    
    # Add src to path
    sys.path.insert(0, 'src')
    
    modules = [
        'database',
        'ingestion',
        'data_quality',
        'kpi_calculator',
        'main'
    ]
    
    all_imported = True
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}.py")
        except Exception as e:
            print(f"❌ {module}.py - Error: {str(e)}")
            all_imported = False
    
    return all_imported

def test_database_schema():
    """Test if database schema is initialized"""
    print_header("Testing Database Schema")
    
    try:
        from database import DatabaseManager
        
        db = DatabaseManager()
        
        # Check if key tables exist
        tables = [
            'dim_date',
            'dim_customers',
            'dim_products',
            'fact_sales',
            'fact_kpis',
            'fact_data_quality'
        ]
        
        all_exist = True
        for table in tables:
            try:
                result = db.query_to_dataframe(f"SELECT COUNT(*) FROM {table}")
                print(f"✅ {table} ({result.iloc[0, 0]} records)")
            except Exception as e:
                print(f"❌ {table} - NOT FOUND")
                all_exist = False
        
        db.close()
        
        if not all_exist:
            print("\n💡 Initialize database: python src/main.py --init-db")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Schema check failed: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "BUSINESS KPI PIPELINE - SYSTEM TEST" + " "*13 + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        ("Python Packages", test_python_packages),
        ("Configuration File", test_config_file),
        ("Directory Structure", test_directory_structure),
        ("Data Files", test_data_files),
        ("Custom Modules", test_module_imports),
        ("Database Connection", test_database_connection),
        ("Database Schema", test_database_schema),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {str(e)}")
            results[test_name] = False
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        print("\n📋 Next steps:")
        print("   1. Run pipeline: python src/main.py --init-db")
        print("   2. Connect Power BI to database")
        print("   3. Build your dashboard")
        return True
    else:
        print("\n⚠️  Some tests failed. Fix issues above and re-run.")
        print("\n💡 Common fixes:")
        print("   • Install packages: pip install -r requirements.txt")
        print("   • Generate data: python src/main.py --generate-data")
        print("   • Init database: python src/main.py --init-db")
        print("   • Check config: config/config.yaml")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)