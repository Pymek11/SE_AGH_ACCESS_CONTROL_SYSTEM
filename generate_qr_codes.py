import os
from datetime import datetime
from sqlalchemy import insert, select
from app.core.database import engine, SessionLocal
from app.models.qr_image import employees
from app.services.qr_generator import (
    generate_qr_code_blob,
    generate_qr_code_file,
)


def generate_and_store_qr_codes(
    num_employees: int = 5,
    employee_names: list = None,
    qr_output_folder: str = "app/static/qr_codes"
) -> None:
    os.makedirs(qr_output_folder, exist_ok=True)
    
    if employee_names is None:
        employee_names = [f"Employee_{i+1}" for i in range(num_employees)]
    
    db = SessionLocal()
    
    try:
        for i, emp_name in enumerate(employee_names[:num_employees]):
            qr_blob = generate_qr_code_blob(emp_name)
            
            qr_filename = f"{emp_name.replace(' ', '_')}.png"
            qr_filepath = os.path.join(qr_output_folder, qr_filename)
            generate_qr_code_file(emp_name, qr_filepath)
            
            # Check if employee already exists by name
            exists_stmt = select(employees.c.emp_id).where(employees.c.emp_name == emp_name)
            existing = db.execute(exists_stmt).first()

            if existing:
                # Do not modify existing DB record
                print(f"• Skipped DB insert: employee '{emp_name}' already exists")
                print(f"  → Regenerated PNG at: {qr_filepath}")
            else:
                stmt = insert(employees).values(
                    emp_name=emp_name,
                    emp_qr_code=qr_blob,
                    emp_photo=None,
                )
                db.execute(stmt)
                print(f"✓ Generated QR for '{emp_name}'")
                print(f"  → Saved PNG to: {qr_filepath}")
                print(f"  → Stored blob in database")
        
        db.commit()
        print(f"\n✓ Successfully generated and stored {len(employee_names[:num_employees])} QR codes!")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    employee_list = [
        "John Doe",
        "Jane Smith",
        "Bob Johnson",
        "Alice Brown",
        "Charlie Wilson"
    ]
    
    generate_and_store_qr_codes(
        num_employees=len(employee_list),
        employee_names=employee_list,
        qr_output_folder="app/static/qr_codes"
    )