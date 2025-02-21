from datetime import datetime
from ..models.summary import Summary

class MarkdownFormatter:
    def __init__(self, output_file: str = "summaries.md"):
        self.output_file = output_file
    
    def append_summary(self, summary: Summary):
        """Prepends a new summary to the markdown file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_content = (
            f"# {summary.title} (ID: {summary.video_id})\n"
            f"*Generated on {timestamp}*\n\n"
            f"{summary.summary_text}\n\n---\n\n"
        )
        
        # Read existing content if file exists
        existing_content = ""
        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                existing_content = f.read()
        except FileNotFoundError:
            pass
        
        # Write new content followed by existing content
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(new_content + existing_content) 