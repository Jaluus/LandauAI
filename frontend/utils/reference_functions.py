import re
from typing import Literal

import chainlit as cl

from .references import (
    BaseReference,
    FormulaReference,
    SectionReference,
    SnippetReference,
)


def to_reference(
    raw_reference: dict,
    reference_type: Literal["section", "snippet", "formula"],
) -> BaseReference:
    assert reference_type in [
        "section",
        "snippet",
        "formula",
    ], "Invalid reference type."

    formatted_input = {
        "document_id": raw_reference["document_id"],
        "chapter_id": raw_reference["chapter_id"],
        "section_id": raw_reference["section_id"],
        "document_name": raw_reference["document_name"],
        "chapter_name": raw_reference["chapter_name"],
        "section_name": raw_reference["section_name"],
        "content": raw_reference["content"],
    }

    if reference_type == "section":
        return SectionReference(
            **formatted_input,
        )

    elif reference_type == "snippet":
        return SnippetReference(
            paragraph_id=raw_reference["paragraph_id"],
            score=raw_reference["score"],
            **formatted_input,
        )

    elif reference_type == "formula":
        return FormulaReference(
            formula_id=raw_reference["formula_id"],
            **formatted_input,
        )


async def add_references_to_messsage(model_message: cl.Message) -> None:
    references: list[BaseReference] = cl.user_session.get("references")

    # Snippet Reference
    # \[[A-Z]+\d+\s\d+\.\d+\/\d+\]
    # [EX1 15.7/1]

    # Section Reference
    # \[[A-Z]+\d+\s\d+\.\d+\]
    # [FEYNMAN2 4.2]

    # Formula Reference
    # \[[A-Z]+\d+\s\d+\.\d+\s\(\d+\.\d+\)\]
    # [EX1 15.7 (1.3)]

    message_text = model_message.content
    available_reference_keys = [ref.reference_key for ref in references]
    # check the message for references using the regex
    found_snippet_keys = re.findall(r"\[[A-Z\d]+\s\d+\.\d+\/\d+\]", message_text)
    found_section_keys = re.findall(r"\[[A-Z\d]+\s\d+\.\d+\]", message_text)
    found_formula_keys = re.findall(
        r"\[[A-Z\d]+\s\d+\.\d+\s\(\d+\.\d+\)\]", message_text
    )
    # we need to strip the brackets from the found references
    found_reference_keys = [
        ref_key[1:-1]
        for ref_key in found_snippet_keys + found_section_keys + found_formula_keys
    ]

    unmatched_reference_keys = [
        ref_key
        for ref_key in list(set(found_reference_keys))
        if ref_key not in available_reference_keys
    ]
    matched_reference_keys = list(
        set(found_reference_keys) - set(unmatched_reference_keys)
    )

    for ref_key in unmatched_reference_keys:
        message_text = message_text.replace(ref_key, f"~~{ref_key}~~")

    # add all the references as side elements. this will only show if the reference is in the text
    elements = [
        cl.Text(
            name=ref.reference_key,
            content=ref.print_reference(),
            display="side",
        )
        for ref in references
        if ref.reference_key in matched_reference_keys
    ]

    if len(unmatched_reference_keys) > 0:
        elements.append(
            cl.Text(
                name="Hinweis!",
                content=f"Das Modell hat wahrscheinlich Halluziniert!\nDie Referenz{'' if len(unmatched_reference_keys) == 1 else 'en'} **{', '.join(unmatched_reference_keys)}** hat das Modell nie gesehen.",
                display="inline",
            )
        )

    model_message.elements = elements
    model_message.content = message_text
    await model_message.update()


def update_references(new_references: list[BaseReference] | BaseReference) -> None:

    if not isinstance(new_references, list):
        new_references = [new_references]

    references: list[BaseReference] = cl.user_session.get("references", [])
    reference_keys = [ref.reference_key for ref in references]

    for reference in new_references:
        reference_key = reference.reference_key
        if reference_key not in reference_keys:
            references.append(reference)
            reference_keys.append(reference_key)
