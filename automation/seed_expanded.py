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
                name="AI Dev Hub",
                description="Central management dashboard for all playground applications.",
                url="https://hub.{DOMAIN}",
                github_url="https://github.com/alshawwaf/dev-hub",
                category="Management",
                icon="/logo.png",
                is_live=True
            ),
            models.Application(
                name="Training Portal",
                description="Enterprise blueprint for virtualized hands-on learning.",
                url="https://training.{DOMAIN}",
                github_url="https://github.com/alshawwaf/training-portal",
                category="Education",
                icon="/logos/training.png",
                is_live=True
            ),
            models.Application(
                name="Lakera Demo",
                description="Interactive playground for testing LLM guardrails.",
                url="https://lakera.{DOMAIN}",
                github_url="https://github.com/alshawwaf/Lakera-Demo",
                category="Security",
                icon="/logos/lakera.png",
                is_live=True
            ),
            models.Application(
                name="n8n Automation",
                description="Workflow automation tool for linking LLMs and services.",
                url="https://n8n.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-agentic-mcp-playground",
                category="Automation",
                icon="/logos/n8n.png",
                is_live=True
            ),
            models.Application(
                name="Flowise AI",
                description="Visual builder for LLM orchestration and agentic flows.",
                url="https://flowise.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-agentic-mcp-playground",
                category="Orchestration",
                icon="/logos/flowise.png",
                is_live=True
            ),
            models.Application(
                name="Langflow Playground",
                description="Alternative visual IDE for building RAG and AI pipelines.",
                url="https://langflow.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-agentic-mcp-playground",
                category="Orchestration",
                icon="/logos/langflow.png",
                is_live=True
            ),
            models.Application(
                name="Docs-to-Swagger",
                description="Automated conversion of documentation to OpenAPI/Swagger specifications.",
                url="https://swagger.{DOMAIN}",
                github_url="https://github.com/alshawwaf/cp-docs-to-swagger",
                category="Tools",
                icon="/logos/swagger.png",
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
