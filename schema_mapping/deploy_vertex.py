"""Deploy the Schema Mapping Agent to Vertex AI."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.adk.agents.llm_agent import Agent
from google.adk.cli import deploy_agent
from schema_mapping.config import config


def deploy_to_vertex_ai():
    """Deploy the schema mapping agent to Vertex AI."""
    
    print("=" * 80)
    print("  Deploying Schema Mapping Agent to Vertex AI")
    print("=" * 80)
    print()
    
    # Check for required configuration
    project_id = config.default_project
    location = config.vertex_ai_location
    
    if not project_id:
        print("❌ Error: GCP_PROJECT environment variable not set")
        print("   Please set it to your Google Cloud project ID")
        sys.exit(1)
    
    print(f"📋 Deployment Configuration:")
    print(f"   Project ID: {project_id}")
    print(f"   Location: {location}")
    print(f"   Agent: schema_mapping_agent")
    print()
    
    # Confirm deployment
    response = input("Proceed with deployment? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Deployment cancelled.")
        sys.exit(0)
    
    print()
    print("🚀 Starting deployment...")
    print()
    
    try:
        # Import the agent
        from schema_mapping.agent import root_agent
        
        # Deploy using ADK
        # Note: This will create/update the agent in Vertex AI
        deployment_result = deploy_agent(
            agent=root_agent,
            project_id=project_id,
            location=location,
            display_name="Schema Mapping Agent",
            description="Intelligent ETL schema mapping assistant for BigQuery tables"
        )
        
        print()
        print("✅ Deployment successful!")
        print()
        print(f"Agent deployed to: {location}")
        print(f"Project: {project_id}")
        print()
        print("📝 Next Steps:")
        print("1. Go to Vertex AI Agent Builder in Google Cloud Console")
        print("2. Find your agent: 'Schema Mapping Agent'")
        print("3. Test the agent in the console")
        print("4. Integrate with your application")
        print()
        
    except Exception as e:
        print(f"❌ Deployment failed: {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Ensure you're authenticated: gcloud auth application-default login")
        print("2. Check that Vertex AI API is enabled in your project")
        print("3. Verify you have necessary IAM permissions:")
        print("   - Vertex AI User")
        print("   - BigQuery User")
        print("4. Make sure all dependencies are installed")
        sys.exit(1)


def configure_iam_permissions():
    """Guide user through setting up IAM permissions."""
    
    print("=" * 80)
    print("  IAM Permission Setup Guide")
    print("=" * 80)
    print()
    
    project_id = config.default_project
    
    print("The Schema Mapping Agent needs the following permissions:")
    print()
    print("1. Vertex AI Permissions:")
    print("   - Vertex AI User")
    print("   - Vertex AI Agent User")
    print()
    print("2. BigQuery Permissions:")
    print("   - BigQuery Data Viewer (to read table schemas)")
    print("   - BigQuery User (to run queries)")
    print()
    
    print("To grant these permissions, run:")
    print()
    print(f"# Get your user email or service account")
    print(f"USER_EMAIL=$(gcloud auth list --filter=status:ACTIVE --format='value(account)')")
    print()
    print(f"# Grant Vertex AI permissions")
    print(f"gcloud projects add-iam-policy-binding {project_id} \\")
    print(f"  --member=\"user:$USER_EMAIL\" \\")
    print(f"  --role=\"roles/aiplatform.user\"")
    print()
    print(f"# Grant BigQuery permissions")
    print(f"gcloud projects add-iam-policy-binding {project_id} \\")
    print(f"  --member=\"user:$USER_EMAIL\" \\")
    print(f"  --role=\"roles/bigquery.dataViewer\"")
    print()
    print(f"gcloud projects add-iam-policy-binding {project_id} \\")
    print(f"  --member=\"user:$USER_EMAIL\" \\")
    print(f"  --role=\"roles/bigquery.user\"")
    print()


def test_deployed_agent():
    """Test the deployed agent."""
    
    print("=" * 80)
    print("  Testing Deployed Agent")
    print("=" * 80)
    print()
    
    print("To test your deployed agent:")
    print()
    print("1. Via Google Cloud Console:")
    print("   - Go to Vertex AI > Agent Builder")
    print("   - Select 'Schema Mapping Agent'")
    print("   - Use the built-in chat interface")
    print()
    print("2. Via API/SDK:")
    print("   - Use the Vertex AI Python SDK")
    print("   - Example code in README.md")
    print()
    print("3. Via Web UI:")
    print("   - Deploy with ADK web interface")
    print("   - Access at generated URL")
    print()


def main():
    """Main entry point for deployment."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deploy Schema Mapping Agent to Vertex AI'
    )
    parser.add_argument(
        '--action',
        choices=['deploy', 'permissions', 'test'],
        default='deploy',
        help='Action to perform'
    )
    parser.add_argument(
        '--project',
        help='GCP Project ID (overrides config)'
    )
    parser.add_argument(
        '--location',
        help='Vertex AI location (overrides config)'
    )
    
    args = parser.parse_args()
    
    # Override config if provided
    if args.project:
        config.default_project = args.project
    if args.location:
        config.vertex_ai_location = args.location
    
    # Execute requested action
    if args.action == 'deploy':
        deploy_to_vertex_ai()
    elif args.action == 'permissions':
        configure_iam_permissions()
    elif args.action == 'test':
        test_deployed_agent()


if __name__ == "__main__":
    main()

