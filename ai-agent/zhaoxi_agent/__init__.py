from langchain.agents import create_agent


class ReactAgent:
    def __init__(self, *, model, system_prompt, tools, middleware=()):
        self.agent = create_agent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            middleware=middleware,
        )
