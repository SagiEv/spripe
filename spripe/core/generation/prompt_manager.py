"""Module docstring."""
import os
import json

# Default animation templates
DEFAULT_TEMPLATES = {
    "asset_design": {"type": "Asset Design", "text": "Character concept art, multiple angles (front, profile), clear silhouette, flat colors, white background."},
    "reference_image": {"type": "Asset Reference Creation", "text": "Dynamic fighting pose, looking forward, pure white background, maintaining character proportions."},
    "idle_animation": {"type": "Asset Animation Creation", "text": "6-12 frames loop. Stand in a ready combat position. Slight breathing motion, natural weight shifting."},
    "walk_forward": {"type": "Asset Animation Creation", "text": "8-12 frames loop. Confident, aggressive forward movement keeping guard up."},
    "punch_light": {"type": "Asset Animation Creation", "text": "4-6 frames. Fast, snappy jab, quick recovery."},
}

class PromptManager:
    """Manages the 3-layer prompt system for generating assets."""

    def __init__(self, project_path: str, workspace_dir: str = None):
        self.project_path = project_path
        self.workspace_dir = workspace_dir
        self.prompts_file = os.path.join(project_path, "prompts.json")
        self.templates = self._load_templates()
        self.global_wrapper = self._load_global_wrapper()

    def _load_global_wrapper(self) -> str:
        """Loads the global wrapper rules."""
        # PLACEHOLDER: You can change this text later when you finalize your rules.
        # Alternatively, you can read from a file by uncommenting the logic below.

        # if self.workspace_dir:
        #     docs_path = os.path.join(self.workspace_dir, "docs", "assetsGenerator.md")
        #     if os.path.exists(docs_path):
        #         try:
        #             with open(docs_path, "r", encoding="utf-8") as f:
        #                 return f.read()
        #         except Exception as e:
        #             pass

        return "GLOBAL REQUIREMENTS:\n- Pure white background (#FFFFFF) only.\n- Full body visible."
    def _load_templates(self) -> dict:
        """Loads templates from the project's prompts.json or creates defaults."""
        if os.path.exists(self.prompts_file):
            try:
                with open(self.prompts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # Migrate old string format to dict format
                    migrated = False
                    for k, v in data.items():
                        if isinstance(v, str):
                            data[k] = {"type": "None", "text": v}
                            migrated = True
                    if migrated:
                        self.save_templates(data)

                    return data
            except Exception as e:
                print(f"Error loading prompts.json: {e}")
                return DEFAULT_TEMPLATES.copy()
        else:
            self.save_templates(DEFAULT_TEMPLATES)
            return DEFAULT_TEMPLATES.copy()

    def save_templates(self, templates: dict):
        """Saves the current templates back to the project."""
        try:
            os.makedirs(os.path.dirname(self.prompts_file), exist_ok=True)
            with open(self.prompts_file, "w", encoding="utf-8") as f:
                json.dump(templates, f, indent=4)
        except Exception as e:
            print(f"Error saving prompts.json: {e}")

    def update_template(self, key: str, template_type: str, new_text: str):
        """Update a specific template and save to disk."""
        self.templates[key] = {"type": template_type, "text": new_text}
        self.save_templates(self.templates)

    def build_prompt(self, template_key: str, user_input: str) -> str:
        """
        Combines the global wrapper, project template, and user input.
        """
        template_obj = self.templates.get(template_key, {})
        template_text = template_obj.get("text", "") if isinstance(template_obj, dict) else template_obj

        parts = [
            "### SYSTEM REQUIREMENTS ###",
            self.global_wrapper.strip(),
            "### STYLE/BASE ACTION ###",
            template_text.strip(),
            "### USER SPECIFIC INPUT ###",
            user_input.strip()
        ]

        return "\n\n".join(parts)
