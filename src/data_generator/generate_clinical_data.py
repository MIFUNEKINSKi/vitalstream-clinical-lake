import xml.etree.ElementTree as ET
from faker import Faker
import boto3
import random
import os
import time

fake = Faker()

def generate_patient_visit():
    # Create Root ODM Element
    root = ET.Element("ODM", xmlns="http://www.cdisc.org/ns/odm/v1.3")
    study = ET.SubElement(root, "Study", OID="VitalStream_001")

    # Simulating a Subject Data Point
    clinical_data = ET.SubElement(root, "ClinicalData", StudyOID="VitalStream_001", MetaDataVersionOID="v1.0")
    subject_data = ET.SubElement(clinical_data, "SubjectData", SubjectKey=str(fake.uuid4()))

    # Add Visit Data (e.g., Vital Signs)
    visit_date = fake.date_this_year().isoformat()
    study_event = ET.SubElement(subject_data, "StudyEventData", StudyEventOID="VISIT_1", EffectiveDate=visit_date)
    form_data = ET.SubElement(study_event, "FormData", FormOID="VS")

    # Heart Rate
    item_group = ET.SubElement(form_data, "ItemGroupData", ItemGroupOID="IG_VS")
    item_data_hr = ET.SubElement(item_group, "ItemData", ItemOID="VS.HR", Value=str(random.randint(60, 100)))

    tree = ET.ElementTree(root)
    file_name = f"visit_{fake.uuid4()}.xml"
    
    # Save locally
    tree.write(file_name)
    print(f"Generated {file_name}")

    # Upload to S3 (Uncomment when Infra is ready)
    # Upload to S3 (Uncomment when Infra is ready)
    bucket_name = "vitalstream-landing-zone-445cb2f1" 
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_name, bucket_name, file_name)
        print(f"Uploaded {file_name} to {bucket_name}")
        os.remove(file_name) # Clean up local file
    except Exception as e:
        print(f"Error uploading to S3: {e}")

if __name__ == "__main__":
    generate_patient_visit()
