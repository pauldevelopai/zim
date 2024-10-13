from google.oauth2 import service_account
from google.cloud import compute_v1

# Path to your service account key file
SERVICE_ACCOUNT_FILE = "path/to/your-service-account-key.json"

# Create credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE
)

# Set project and zone information
project_id = "your_project_id"
zone = "us-central1-a"  # As per your screenshot

# Create the Compute Engine client
compute_client = compute_v1.InstancesClient(credentials=credentials)

# List all instances in a specific zone
def list_instances(project, zone):
    request = compute_v1.ListInstancesRequest(
        project=project,
        zone=zone
    )
    response = compute_client.list(request)
    for instance in response.items:
        print(f"Instance Name: {instance.name}, Status: {instance.status}")

# Example usage
list_instances(project_id, zone)