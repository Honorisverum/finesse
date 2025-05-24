from typing import Literal

from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.types import Command, interrupt
from langchain_core.messages import HumanMessage


model = ChatOpenAI(temperature=0, model_name="gpt-4o")


# def call_model(state: MessagesState) -> Command[Literal["human", END]]:
#     messages = state["messages"]
#     response = model.invoke(messages)
#     return Command(
#         goto="human",
#         update={"messages": [response]},
#     )


def call_model(state: MessagesState) -> MessagesState:
    messages = state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


# def human_feedback(state: MessagesState) -> Command[Literal["agent"]]:
#     """A node for collecting user input."""
#     print("Waiting for user input...")
#     user_input = interrupt(value="Ready for user input.")
#     print("user input:", user_input)
#     return Command(
#         goto="agent",
#         update={
#             "messages": [
#                 {
#                     "role": "human",
#                     "content": user_input,
#                 }
#             ]
#         },
#     )


def human_feedback(state: MessagesState) -> MessagesState:
    """A node for collecting user input."""
    print("Waiting for user input...")
    user_input = interrupt(value="Ready for user input.")
    print("user input:", user_input)
    msg = HumanMessage(content=user_input)
    return {"messages": state["messages"] + [msg]}



# def human_feedback(state: MessagesState) -> MessagesState:
#     pass


def should_continue(state: MessagesState):
    last_message = state["messages"][-1]
    if last_message.content.lower() in ["exit", "quit", "stop"]:
        return "end"
    else:
        return "agent"


workflow = StateGraph(MessagesState)
workflow.set_entry_point("agent")
workflow.add_node("agent", call_model)
workflow.add_node("human", human_feedback)
workflow.add_edge("agent", "human")
workflow.add_conditional_edges(
    "human",
    path=should_continue,
    path_map={
        "agent": "agent",
        "end": END,
    },
)

graph = workflow.compile()
