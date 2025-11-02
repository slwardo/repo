gcloud stuff

## gcloud auth
gcloud auth application-default login
gcloud auth application-default revoke


python3 pstoremetricsv2.py --project_id thomashk-mig --instance_id instance-default --start_date 2025-05-14


gcloud projects get-iam-policy lab-gke-se --flatten="bindings[].members" --format='table(bindings.role,bindings.members)' --filter="bindings.members:stefanward@gc-trial-0041.orgtrials.ongcp.co"

gcloud projects add-iam-policy-binding lab-gke-se \
    --member="user:stefanward@google.com" \
    --role="roles/monitoring.viewer"

gcloud auth print-access-token --impersonate-service-account=service-594050280394@gcp-sa-logging.iam.gserviceaccount.com


gcloud iam service-accounts add-iam-policy-binding "SERVICE_ACCOUNT_EMAIL" \
    --project="thomashk-mig" \
    --member="user:USER_EMAIL" \
    --role="roles/iam.serviceAccountTokenCreator"



    gcloud iam service-accounts add-iam-policy-binding "stefan-test1@thomashk-mig.iam.gserviceaccount.com" \
    --project="lab-gke-se" \
    --member="user:stefanward@google.com" \
    --role="roles/iam.serviceAccountTokenCreator"

gcloud beta parallelstore instances list \
    --project="thomashk-mig" \
    --location="-" \
    --format="table(name.segment(-1):label=INSTANCE_NAME, location.segment(-1):label=LOCATION, createTime) \
gcloud beta parallelstore instances list \
    --project="thomashk-mig" \
    --location="-" \
    --format="table(
        name.segment(-1):label=INSTANCE_NAME,
        name.segment(3):label=LOCATION,
        createTime
    )
INSTANCE_NAME                             LOCATION       CREATE_TIME
instance                                  us-central1-a  2025-04-22T20:10:29.214167350Z
scratchtest1                              us-central1-a  2025-04-15T14:38:46.541495853Z
pvc-d13842ae-2bd4-4602-bd11-002eb1197011  us-central1-b  2025-04-25T20:33:54.972898428Z
