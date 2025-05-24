import gradio as gr

from posneg import posneg
from agentic import agentic
from mdagaw import mdagaw


with gr.Blocks(title="Finesse Chat") as demo:
    gr.Markdown("# Finesse App - People Skills Training")
    gr.Markdown("## Choose a mode: 1)PosNeg 2)Agentic 3)Mdagaw")

with demo.route("PosNeg"):
    gr.Markdown("# Finesse App - People Skills Training")
    posneg.demo.render()

with demo.route("Agentic"):
    gr.Markdown("# Finesse App - People Skills Training")
    agentic.demo.render()

with demo.route("Mdagaw"):
    gr.Markdown("# Finesse App - People Skills Training")
    mdagaw.demo.render()

if __name__ == "__main__":
    demo.launch()
