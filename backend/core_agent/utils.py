import os
import glob

_HERE = os.path.dirname(os.path.abspath(__file__))
from langchain_core.messages import SystemMessage

class DocumentAndPromptLoader:
    """
    Utility helper to handle loading, parsing, and context-caching of documents and prompts.
    """
    def __init__(self, docs_dir=None, prompt_path=None):
        """
        Initializes the DocumentAndPromptLoader.
        
        Args:
            docs_dir: Directory containing knowledge files.
            prompt_path: Core instructions markdown path.
        """
        self.docs_dir = docs_dir or os.path.join(_HERE, "docs")
        self.prompt_path = prompt_path or os.path.join(_HERE, "prompts", "system_prompt.md")
        self.doc_registry = {}
        self.doc_descriptions = []
        self.permanent_context = ""
        
        self.classifier_prompt = ""
        self.emotion_analysis_prompt = ""
        self.brand_audit_prompt = ""
        self.fact_audit_prompt = ""
        self.emotional_audit_prompt_template = ""
        self.output_guardrail_prompt = ""
        self.quick_fix_prompt = ""
        self.static_prompt_content = ""
        
        self.load_and_parse_documents()
        self.load_all_prompts()
        
    def _parse_doc(self, filepath):
        """
        Parses metadata headers and text body from a markdown document.
        
        Args:
            filepath: Path to markdown file.
            
        Returns:
            A tuple of (metadata_dict, body_text).
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_raw = parts[1]
                body = parts[2].strip()
                metadata = {}
                for line in frontmatter_raw.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        metadata[k.strip()] = v.strip()
                return metadata, body
        return {}, content.strip()

    def load_and_parse_documents(self):
        """
        Scans docs_dir, preloading static files into memory and registering 
        dynamic files for retrieval tools.
        """
        md_files = glob.glob(os.path.join(self.docs_dir, "*.md"))
        for filepath in md_files:
            filename = os.path.basename(filepath)
            if filename in ["brand_identity.md", "customer_service_sop.md"]:
                _, body = self._parse_doc(filepath)
                self.permanent_context += f"\n--- {filename} ---\n{body}\n"
            else:
                meta, body = self._parse_doc(filepath)
                name = meta.get("name", filename.replace(".md", ""))
                description = meta.get("description", "No description provided.")
                self.doc_registry[name.lower()] = body
                self.doc_descriptions.append(f"- '{name}': {description}")

    def load_prompt_file(self, filename):
        """
        Loads a prompt template string from prompts directory.
        
        Args:
            filename: Filename within prompts folder.
            
        Returns:
            The loaded template string.
            
        Raises:
            FileNotFoundError if target file is missing.
        """
        path = os.path.join(_HERE, "prompts", filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required prompt file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    def load_system_prompt(self):
        """
        Loads the concierge system instructions.
        
        Returns:
            Concierge instructions string.
            
        Raises:
            FileNotFoundError if missing in all default locations.
        """
        possible_paths = [
            self.prompt_path,
            os.path.join(_HERE, "prompts", "system_prompt.txt"),
            os.path.join(_HERE, "prompts", "system_prompt.md"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        raise FileNotFoundError(f"Required system prompt file not found in paths: {possible_paths}")

    def load_all_prompts(self):
        """
        Loads all modular prompt file contents.
        """
        self.classifier_prompt = self.load_prompt_file("classifier.md")
        self.emotion_analysis_prompt = self.load_prompt_file("emotion_analysis.md")
        self.brand_audit_prompt = self.load_prompt_file("brand_audit.md")
        self.fact_audit_prompt = self.load_prompt_file("fact_audit.md")
        self.emotional_audit_prompt_template = self.load_prompt_file("emotional_audit.md")
        self.output_guardrail_prompt = self.load_prompt_file("output_guardrail.md")
        self.quick_fix_prompt = self.load_prompt_file("quick_fix.md")

    def setup_static_prompt(self):
        """
        Assembles static instruction files and preloads them into self.static_prompt_content.
        """
        system_prompt = self.load_system_prompt()
        doc_list_str = "\n".join(self.doc_descriptions)
        self.static_prompt_content = (
            f"{system_prompt}\n\n"
            f"=== PERMANENT CONTEXT ===\n{self.permanent_context}\n\n"
            f"=== KNOWLEDGE DOCUMENTS AVAILABLE VIA TOOL ===\n"
            f"You have access to a tool `retrieve_document_content` which can fetch details for:\n"
            f"{doc_list_str}\n\n"
            f"=== ORDER TRACKING DATABASE TOOL ===\n"
            f"You have access to a tool `look_up_order` which can fetch live tracking and shipment details for an order ID or phone number."
        )


    def reload_documents(self):
        """
        Reloads all documents dynamically from docs_dir.
        """
        self.doc_registry = {}
        self.doc_descriptions = []
        self.permanent_context = ""
        self.load_and_parse_documents()
        self.setup_static_prompt()

