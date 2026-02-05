from db.database import SessionLocal
from db import models
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def seed():
    db = SessionLocal()
    try:
        # 0. Basic Configuration
        DOMAIN = os.getenv("DOMAIN", "cpdemo.ca")
        
        # 1. Seed Superadmin
        admin_email = os.getenv("SUPERADMIN_EMAIL", f"admin@{DOMAIN}")
        admin_password = os.getenv("SUPERADMIN_PASSWORD", "Cpwins!1@2026")
        
        user = db.query(models.User).filter(models.User.email == admin_email).first()
        if not user:
            print(f"Seeding superadmin user: {admin_email}")
            new_user = models.User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                is_admin=True
            )
            db.add(new_user)
            db.commit()
            print("Superadmin seeded successfully.")
        else:
            print("Superadmin already exists.")
            
        # 2. Clear existing applications
        print("Clearing existing applications...")
        db.query(models.Application).delete()
        db.commit()

        # 3. Seed expanded applications with project groupings
        print("Seeding applications with groupings...")
        apps = [
            models.Application(
                name="Lakera Guard Demo",
                description="AI security guardrails",
                url=f"https://lakera.{DOMAIN}",
                github_url="https://github.com/alshawwaf/Lakera-Demo",
                category="AI Security",
                icon="security",
                is_live=True
            ),
            models.Application(
                name="Training Portal",
                description="AI development training platform",
                url=f"https://training.{DOMAIN}",
                github_url="https://github.com/alshawwaf/training-portal",
                category="Training",
                icon="training",
                is_live=True
            ),
            models.Application(
                name="Docs to Swagger",
                description="Convert API docs to OpenAPI",
                url=f"https://swagger.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-docs-to-swagger",
                category="Developer Tools",
                icon="swagger",
                is_live=True
            ),
            models.Application(
                name="n8n Workflow",
                description="AI workflow automation platform",
                url=f"https://workflow.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-agentic-mcp-playground",
                category="Automation",
                icon="n8n",
                is_live=True
            ),
            models.Application(
                name="Open WebUI",
                description="Chat interface for AI models",
                url=f"https://chat.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-agentic-mcp-playground",
                category="AI Chat",
                icon="chat",
                is_live=True
            ),
            models.Application(
                name="Flowise",
                description="Visual LLM flow builder",
                url=f"https://flowise.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-agentic-mcp-playground",
                category="AI Development",
                icon="flowise",
                is_live=True
            ),
            models.Application(
                name="Langflow",
                description="Visual AI pipeline designer",
                url=f"https://langflow.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-agentic-mcp-playground",
                category="AI Development",
                icon="langflow",
                is_live=True
            ),
        ]
        db.add_all(apps)
        db.commit()
        print("Grouped applications seeded successfully.")
            
    finally:
        db.close()

if __name__ == "__main__":
    seed()
