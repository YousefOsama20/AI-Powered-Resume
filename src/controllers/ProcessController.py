import os
import re
from typing import List, Dict, Union
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .BaseController import BaseController
from .ProjectController import ProjectController
from .loaderController import load_pdf, load_docx
from models.enums import ProcessingEnum, ResumeSectionEnum, SECTION_PATTERNS


class ProcessController(BaseController):

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str) -> str:
        return os.path.splitext(file_id)[-1].lower()

    def get_file_loader(self, file_id: str) -> list:
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return []

        if file_ext == ProcessingEnum.PDF.value:
            return load_pdf(file_path)

        if file_ext == ProcessingEnum.DOCX.value:
            return load_docx(file_path)

        return []

    def get_file_content(self, file_id: str) -> list:
        return self.get_file_loader(file_id=file_id)

    def clean_text(self, text: str) -> str:
        """Strip control characters and normalize whitespace."""
        if not text:
            return ""
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n+', '\n\n', cleaned)
        return cleaned.strip()

    def match_section_header(self, line: str) -> Union[str, None]:
        """Checks if a single line matches any standard resume section header."""
        stripped = line.strip()
        if not stripped or len(stripped) > 40:
            return None

        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(stripped):
                return section_name
        return None

    def segment_text_into_sections(self, full_text: str) -> Dict[str, str]:
        """
        Parses full resume text into classified sections.
        Lines before the first identified section are tagged as Summary.
        """
        lines = full_text.splitlines()
        sections: Dict[str, List[str]] = {}
        current_section = ResumeSectionEnum.SUMMARY.value
        sections[current_section] = []

        for line in lines:
            detected_section = self.match_section_header(line)
            if detected_section:
                current_section = detected_section
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections[current_section].append(line)

        cleaned_sections = {}
        for section_name, section_lines in sections.items():
            content = self.clean_text("\n".join(section_lines))
            if content:
                cleaned_sections[section_name] = content

        return cleaned_sections

    def process_file_content(self,file_content: List[Union[Document, dict, str]],
                                file_id: str,chunk_size: int = 500,overlap_size: int = 50) -> List[Document]:
        """
        1. Aggregates and cleans document text.
        2. Detects sections (Skills, Experience, Education, Projects, Certifications).
        3. Chunks each section with section title tagged in metadata and content.
        """
        if not file_content:
            return []

        # 1. Combine all document pages into one full text
        page_texts = []
        for doc in file_content:
            if isinstance(doc, Document):
                page_texts.append(doc.page_content)
            elif isinstance(doc, dict):
                page_texts.append(doc.get("text", doc.get("page_content", "")))
            else:
                page_texts.append(str(doc))

        combined_text = "\n".join(page_texts)

        # 2. Segment by resume sections
        segmented_sections = self.segment_text_into_sections(combined_text)

        # 3. Text Splitter for oversized sections
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

        all_chunks: List[Document] = []
        global_chunk_idx = 0

        # 4. Create chunks for each section
        for section_name, section_text in segmented_sections.items():
            if len(section_text) <= chunk_size:
                sub_chunks = [section_text]
            else:
                sub_chunks = text_splitter.split_text(section_text)

            for sub_idx, sub_chunk_text in enumerate(sub_chunks):
                formatted_content = f"[{section_name}]\n{sub_chunk_text}"

                metadata = {
                    "project_id": str(self.project_id),
                    "file_id": file_id,
                    "section": section_name,
                    "section_chunk_index": sub_idx,
                    "chunk_index": global_chunk_idx,
                    "chunk_id": f"{file_id}_{section_name.replace(' ', '_').lower()}_{sub_idx}"
                }

                all_chunks.append(Document(page_content=formatted_content, metadata=metadata))
                global_chunk_idx += 1

        return all_chunks
