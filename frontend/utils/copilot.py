import chainlit as cl

from .tools import retrieve_section_no_step


async def add_context_to_copilot() -> None:
    if cl.user_session.get("copilot_context", None) is not None:
        return None

    # we are calling a function embedded in the copilot .js file
    # This function fetches the current page URL from the browser
    page_url = await cl.CopilotFunction(name="fetch_page_URL", args={}).acall()

    # Main landing page, dont add any context
    if page_url == "https://phyphox.org/ex1/script/moodle.php":
        return None

    else:
        # https://phyphox.org/ex1/script/moodle.php?package=1&chapter=6.1
        # https://phyphox.org/ex1/script/moodle.php?package=1&chapter=6
        query_args = page_url.split("?")[1]

        # remove everyting after the # from the query_args
        # To remove the fragment identifier from the URL
        query_args = query_args.split("#")[0]

        # parse the query_args to a json object
        query_args = dict([arg.split("=") for arg in query_args.split("&")])

        section_id = query_args.get("chapter", None)
        package_id = query_args.get("package", None)

        if section_id is None or package_id is None:
            return None

        # if no dots are in the chapter_id, add a .1 to the end
        # just be consistent with the chapter_id format
        if "." not in section_id:
            section_id += ".1"

        if package_id == "1":
            document_id = "EX1"
        elif package_id == "2":
            document_id = "EX2"
        else:
            return None

        chapter = await retrieve_section_no_step(document_id, section_id)
        cl.user_session.set("copilot_context", chapter)
