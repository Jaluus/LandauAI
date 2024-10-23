from typing import Literal


class BaseReference:
    reference_key: str
    content: str

    def print_reference(
        self,
        language: Literal["de", "en"] = "de",
    ) -> str:
        raise NotImplementedError

    def genereate_reference_key(self) -> str:
        raise NotImplementedError


class SectionReference(BaseReference):
    def __init__(
        self,
        document_name: str,
        chapter_name: str,
        section_name: str,
        document_id: str,
        chapter_id: str,
        section_id: str,
        content: str,
    ) -> None:
        self.document_name = document_name
        self.chapter_name = chapter_name
        self.section_name = section_name
        self.document_id = document_id
        self.chapter_id = chapter_id
        self.section_id = section_id
        self.content = content
        self.reference_key = self.genereate_reference_key()

    def print_reference(
        self,
        language: Literal["de", "en"] = "de",
    ) -> str:
        if language == "de":
            return (
                f"## Sektions Referenz\n"
                f"**Zitationsschlüssel**: [{self.reference_key}]\n"
                f"**Dokumenten ID**: {self.document_id}\n"
                f"**Dokumentenname**: {self.document_name}\n"
                f"**Kapitel ID**: {self.chapter_id}\n"
                f"**Kapitel**: {self.chapter_name}\n"
                f"**Sektion ID**: {self.section_id}\n"
                f"**Sektion**: {self.section_name}\n"
                f"**Inhalt**:\n{self.content}"
            )
        elif language == "en":
            return (
                f"## Section Reference\n"
                f"**Citation Key**: [{self.reference_key}]\n"
                f"**Document ID**: {self.document_id}\n"
                f"**Document Name**: {self.document_name}\n"
                f"**Chapter ID**: {self.chapter_id}\n"
                f"**Chapter**: {self.chapter_name}\n"
                f"**Section ID**: {self.section_id}\n"
                f"**Section**: {self.section_name}\n"
                f"**Content**:\n{self.content}"
            )
        else:
            raise ValueError(f"Language '{language}' not supported")

    def genereate_reference_key(self) -> str:
        return f"{self.document_id} {self.chapter_id}.{self.section_id}"

    def __repr__(self) -> str:
        return self.reference_key


class SnippetReference(BaseReference):
    def __init__(
        self,
        document_name: str,
        chapter_name: str,
        section_name: str,
        document_id: str,
        chapter_id: str,
        section_id: str,
        paragraph_id: str,
        score: float,
        content: str,
    ) -> None:
        self.document_name = document_name
        self.chapter_name = chapter_name
        self.section_name = section_name
        self.document_id = document_id
        self.chapter_id = chapter_id
        self.section_id = section_id
        self.paragraph_id = paragraph_id
        self.score = score
        self.content = content
        self.reference_key = self.genereate_reference_key()

    def print_reference(
        self,
        language: Literal["de", "en"] = "de",
    ) -> str:
        if language == "de":
            return (
                f"## Snippet Referenz\n"
                f"**Zitationsschlüssel**: [{self.reference_key}]\n"
                f"**Dokumenten ID**: {self.document_id}\n"
                f"**Dokumentenname**: {self.document_name}\n"
                f"**Kapitel ID**: {self.chapter_id}\n"
                f"**Kapitel**: {self.chapter_name}\n"
                f"**Sektion ID**: {self.section_id}\n"
                f"**Sektion**: {self.section_name}\n"
                f"**Paragraph ID**: {self.paragraph_id}\n"
                f"**Score**: {self.score:.1%}\n"
                f"**Inhalt**:\n{self.content}"
            )
        elif language == "en":
            return (
                f"## Snippet Reference\n"
                f"**Citation Key**: [{self.reference_key}]\n"
                f"**Document ID**: {self.document_id}\n"
                f"**Document Name**: {self.document_name}\n"
                f"**Chapter ID**: {self.chapter_id}\n"
                f"**Chapter**: {self.chapter_name}\n"
                f"**Section ID**: {self.section_id}\n"
                f"**Section**: {self.section_name}\n"
                f"**Paragraph ID**: {self.paragraph_id}\n"
                f"**Score**: {self.score:.1%}\n"
                f"**Content**:\n{self.content}"
            )
        else:
            raise ValueError(f"Language '{language}' not supported")

    def genereate_reference_key(self) -> str:
        return f"{self.document_id} {self.chapter_id}.{self.section_id}/{self.paragraph_id}"

    def __repr__(self) -> str:
        return self.reference_key


class FormulaReference(BaseReference):
    def __init__(
        self,
        document_name: str,
        chapter_name: str,
        section_name: str,
        document_id: str,
        chapter_id: str,
        section_id: str,
        formula_id: str,
        content: str,
    ) -> None:
        self.document_name = document_name
        self.chapter_name = chapter_name
        self.section_name = section_name
        self.document_id = document_id
        self.chapter_id = chapter_id
        self.section_id = section_id
        self.formula_id = formula_id
        self.content = content
        self.reference_key = self.genereate_reference_key()

    def print_reference(
        self,
        language: Literal["de", "en"] = "de",
    ) -> str:
        if language == "de":
            return (
                f"## Formel Referenz\n"
                f"**Zitationsschlüssel**: [{self.reference_key}]\n"
                f"**Dokumenten ID**: {self.document_id}\n"
                f"**Dokumentenname**: {self.document_name}\n"
                f"**Kapitel ID**: {self.chapter_id}\n"
                f"**Kapitel**: {self.chapter_name}\n"
                f"**Sektion ID**: {self.section_id}\n"
                f"**Sektion**: {self.section_name}\n"
                f"**Formel ID**: {self.formula_id}\n"
                f"**Inhalt**:\n{self.content}"
            )
        elif language == "en":
            return (
                f"## Formula Reference\n"
                f"**Citation Key**: [{self.reference_key}]\n"
                f"**Document ID**: {self.document_id}\n"
                f"**Document Name**: {self.document_name}\n"
                f"**Chapter ID**: {self.chapter_id}\n"
                f"**Chapter**: {self.chapter_name}\n"
                f"**Section ID**: {self.section_id}\n"
                f"**Section**: {self.section_name}\n"
                f"**Formula ID**: {self.formula_id}\n"
                f"**Content**:\n{self.content}"
            )
        else:
            raise ValueError(f"Language '{language}' not supported")

    def genereate_reference_key(self) -> str:
        return f"{self.document_id} {self.chapter_id}.{self.section_id} ({self.formula_id})"

    def __repr__(self) -> str:
        return self.reference_key
