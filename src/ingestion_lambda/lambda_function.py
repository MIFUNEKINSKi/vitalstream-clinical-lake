import json
import boto3
import pandas as pd
import xml.etree.ElementTree as ET
import io
import datetime

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    print("Event:", json.dumps(event))
    
    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read()
        
        # Parse XML
        root = ET.fromstring(file_content)
        
        # Namespace handling (CDISC ODM often has namespaces)
        # For simplicity in this demo, we'll try to ignore namespaces or handle the default one if present.
        # The generator uses: xmlns="http://www.cdisc.org/ns/odm/v1.3"
        ns = {'odm': 'http://www.cdisc.org/ns/odm/v1.3'}
        
        # Extract Data
        # We need to find the SubjectData and ItemData
        # Path: ClinicalData -> SubjectData -> StudyEventData -> FormData -> ItemGroupData -> ItemData
        
        data_rows = []
        
        # Helper to find with namespace
        def find_all(element, path):
            return element.findall(path, ns)
            
        clinical_data = find_all(root, 'odm:ClinicalData')
        if not clinical_data:
             # Try without namespace if that failed (resilience)
             clinical_data = root.findall('ClinicalData')
             if not clinical_data:
                 print("No ClinicalData found")
                 return
        
        for cd in clinical_data:
            subject_data_list = cd.findall('odm:SubjectData', ns)
            for sd in subject_data_list:
                subject_id = sd.get('SubjectKey')
                
                study_event_data_list = sd.findall('odm:StudyEventData', ns)
                for sed in study_event_data_list:
                    visit_date = sed.get('EffectiveDate') # We added this in generator
                    
                    form_data_list = sed.findall('odm:FormData', ns)
                    for fd in form_data_list:
                        
                        item_group_data_list = fd.findall('odm:ItemGroupData', ns)
                        for igd in item_group_data_list:
                            
                            item_data_list = igd.findall('odm:ItemData', ns)
                            for item in item_data_list:
                                item_oid = item.get('ItemOID')
                                value = item.get('Value')
                                
                                # Specific parsing for our requirement
                                if item_oid == 'VS.HR':
                                    row = {
                                        'SubjectID': subject_id,
                                        'VisitDate': visit_date,
                                        'HeartRate': int(value) if value else None,
                                        'ExtractionTime': datetime.datetime.now().isoformat()
                                    }
                                    data_rows.append(row)
        
        if not data_rows:
            print("No data extracted")
            return {
                'statusCode': 200,
                'body': json.dumps('No data found in XML')
            }
            
        # Convert to DataFrame
        df = pd.DataFrame(data_rows)
        print("Dataframe created:\n", df.head())
        
        # Write to Parquet
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, index=False, engine='pyarrow')
        
        # Define Curated Bucket (replace string with Env Var in real production)
        # For this demo, we assume the bucket name convention or pass it via environment variable.
        # But we don't have the curated bucket name in the event directly unless we infer it.
        # We will assume a naming convention: landing-zone -> curated-zone
        curated_bucket = bucket.replace("landing-zone", "curated-zone")
        
        # Generate Output Key
        output_key = key.replace('.xml', '.parquet')
        
        # Upload
        s3_client.put_object(Bucket=curated_bucket, Key=output_key, Body=parquet_buffer.getvalue())
        print(f"Uploaded parquet to s3://{curated_bucket}/{output_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully processed {key}')
        }
        
    except Exception as e:
        print(e)
        raise e
