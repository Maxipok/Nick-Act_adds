# %% [markdown] 
# # Stress-testing our results
# At this point, we've shown a lot of cool results, but qualitative data
# is fickle and subject to both selection effects and confirmation bias.

# %%
!%load_ext autoreload
!%autoreload 2

# %%
try:
    import algebraic_value_editing
except ImportError:
    commit = "eb1b349"  # Stable commit
    get_ipython().run_line_magic(  # type: ignore
        magic_name="pip",
        line=(
            "install -U"
            f" git+https://github.com/montemac/algebraic_value_editing.git@{commit}"
        ),
    )


# %%
import torch
import pandas as pd 
from typing import List
from jaxtyping import Float

from functools import partial
from transformer_lens.HookedTransformer import HookedTransformer

from algebraic_value_editing import hook_utils 
from algebraic_value_editing.prompt_utils import RichPrompt, get_x_vector

# %%
model_name = "gpt2-xl"

device: str = "cuda:3" if torch.cuda.is_available() else "cpu"
model: HookedTransformer = HookedTransformer.from_pretrained(
    model_name, device="cpu"
)
_ = model.to(device)
_ = torch.set_grad_enabled(False)
torch.manual_seed(0) # For reproducibility

# %% [markdown]
# ## Measuring the magnitudes of the steering vectors at each residual stream position
# How "big" are our edits, compared to the normal activations? Let's first
# examine what the residual stream magnitudes tend to be, by taking the L2
# norm of the residual stream at each sequence position. We'll do this for
# a range of prompts at a range of locations in the forward pass.
# 
# (Most of the below prompts were generated by GPT4.)

# %%
prompt_magnitudes: List[Float[torch.Tensor, "position"]] = []
prompts: List[str] = [
    "Bush did 9/11 because",
    "Barack Obama was born in",
    "Shrek starts off in a swamp",
    "I went up to my friend and said",
    "I talk about weddings constantly",
    "I bring up weddings in every situation",
    (
        "I hate talking about weddings. Instead, let's talk about a totally"
        " different topic, like the impact of NGDP on the price of gold."
    ),
    "Artificial intelligence is transforming industries and reshaping the way we live, work, and interact.",
    "Climate change is one of the most pressing issues of our time, and we must take immediate action to reduce our carbon footprint.",
    "The rise of electric vehicles has led to an increased demand for lithium-ion batteries, driving innovation in the field of battery technology.",
    "The blockchain technology has the potential to revolutionize industries such as finance, supply chain management, and digital identity verification.",
    "CRISPR-Cas9 is a groundbreaking gene editing technology that allows scientists to make precise changes to an organism's DNA.",
    "Quantum computing promises to solve problems that are currently intractable for classical computers, opening up new frontiers in fields like cryptography and materials science.",
    "Virtual reality and augmented reality are transforming the way we experience and interact with digital content.",
    "3D printing is revolutionizing manufacturing, enabling the creation of complex and customized products on demand.",
    "The Internet of Things (IoT) is connecting everyday objects to the internet, providing valuable data and insights for businesses and consumers.",
    "Machine learning algorithms are becoming increasingly sophisticated, enabling computers to learn from data and make predictions with unprecedented accuracy.",
    "Renewable energy sources like solar and wind power are essential for reducing greenhouse gas emissions and combating climate change.",
    "The development of autonomous vehicles has the potential to greatly improve safety and efficiency on our roads.",
    "The human microbiome is a complex ecosystem of microbes living in and on our bodies, and its study is shedding new light on human health and disease.",
    "The use of drones for delivery, surveillance, and agriculture is rapidly expanding, with many companies investing in drone technology.",
    "The sharing economy, powered by platforms like Uber and Airbnb, is disrupting traditional industries and changing the way people access goods and services.",
    "Deep learning is a subset of machine learning that uses neural networks to model complex patterns in data.",
    "The discovery of exoplanets has fueled the search for extraterrestrial life and advanced our understanding of planetary systems beyond our own.",
    "Nanotechnology is enabling the development of new materials and devices at the atomic and molecular scale.",
    "The rise of big data is transforming industries, as companies seek to harness the power of data analytics to gain insights and make better decisions.",
    "Advancements in robotics are leading to the development of robots that can perform complex tasks and interact with humans in natural ways.",
    "The gig economy is changing the nature of work, as more people turn to freelancing and contract work for flexibility and autonomy.",
    "The Mars rover missions have provided valuable data on the geology and climate of the Red Planet, paving the way for future manned missions.",
    "The development of 5G networks promises faster and more reliable wireless connectivity, enabling new applications in areas like IoT and smart cities.",
    "Gene therapy offers the potential to treat genetic diseases by replacing, modifying, or regulating specific genes.",
    "The use of facial recognition technology raises important questions about privacy, surveillance, and civil liberties.",
    "Precision agriculture uses data and technology to optimize crop yields and reduce environmental impacts.",
    "Neuromorphic computing aims to develop hardware that mimics the structure and function of the human brain.",
    "Breaking news: Local man wins the lottery and plans to donate half of his earnings to charity",
    "How to grow your own organic vegetables in your backyard – step by step guide",
    "omg I can't believe this new phone has such a terrible battery life, it doesn't even last a full day!",
    "Top 10 travel destinations you must visit before you die",
    "What are the best ways to invest in cryptocurrency?",
    "I've been using this acne cream for a month and it's only making my skin worse, anyone else having this issue?",
    "The secret to a happy and healthy relationship is communication and trust",
    "Rumor has it that the famous celebrity couple is getting a divorce",
    "I recently switched to a vegan diet and I feel so much better, I can't believe I didn't do it sooner",
    "Can someone help me with my math homework? I'm stuck on this problem...",
    "UFO sightings have increased in the past few years, are we close to making contact with extraterrestrial life?",
    "The government is hiding the truth about climate change and how it's affecting our planet",
    "Are video games causing violence among teenagers? A new study says yes",
    "A new study reveals the benefits of drinking coffee every day",
    "lol this new meme is hilarious, I can't stop laughing!",
    "I'm so tired of people arguing about politics on the internet, can't we all just get along?",
    "I love this new TV show, the characters are so well-developed and the plot is amazing",
    "A devastating earthquake hit the city last night, leaving thousands homeless",
    "Scientists discover a new species of fish deep in the ocean",
    "Why are people still believing in flat earth theory?",
    "The local animal shelter is holding an adoption event this weekend, don't miss it!",
    "The city is planning to build a new park in the neighborhood, residents are excited",
    "My dog ate my homework, literally, can anyone relate?",
    "This new diet trend is taking the world by storm, but is it really effective?",
] 

# %% 
activation_locations: List[int] = torch.arange(0, 48, 6).tolist()

# Create an empty dataframe with the required columns
prompt_df = pd.DataFrame(
    columns=["Prompt", "Activation Location", "Activation Name", "Magnitude"]
)

from algebraic_value_editing import prompt_utils

# Loop through activation locations and prompts
for act_loc in activation_locations:
    act_name: str = prompt_utils.get_block_name(block_num=act_loc)
    for prompt in prompts:
        mags: torch.Tensor = hook_utils.prompt_magnitudes(
            model=model, prompt=prompt, act_name=act_name
        ).cpu()

        # Create a new dataframe row with the current data
        row = pd.DataFrame(
            {
                "Prompt": prompt,
                "Activation Location": act_loc,
                "Activation Name": act_name,
                "Magnitude": mags,
            }
        )

        # Append the new row to the dataframe
        prompt_df = pd.concat([prompt_df, row], ignore_index=True)

# %% [markdown]
# ## Plotting the distribution of activation magnitudes
# As the forward pass progresses through the network, the residual
# stream tends to increase in magnitude in an exponential fashion. This
# is easily visible in the histogram below, which shows the distribution
# of activation magnitudes for each layer of the network. The activation
# distribution translates by an almost constant factor each 6 layers,
# and the x-axis (magnitude) is log-scale, so magnitude apparently
# increases exponentially with layer number.
# 
# (Intriguingly, there are a few outlier residual streams which have
# magnitude over an order of magnitude larger than the rest.)
# %%
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

prompt_df["LogMagnitude"] = np.log10(prompt_df["Magnitude"])
fig = px.histogram(prompt_df, x="LogMagnitude", color="Activation Location",
           marginal="rug", histnorm="percent", nbins=100, opacity=0.5, barmode="overlay", color_discrete_sequence=px.colors.sequential.Rainbow[::-1])

fig.update_layout(legend_title_text="Layer Number",
                  title="Activation Magnitude Distribution by Layer Number",
                  xaxis_title="Magnitude (log 10)",
                  yaxis_title="Percentage of layer activations")

fig.show()

# %% [markdown]
# ## Plotting steering vector magnitudes against layer number
# Let's see whether the steering vector magnitudes also increase
# exponentially with layer number. It turns out that the answer is yes,
# although the zeroth token (the <|endoftext|> token) has a much larger
# magnitude than the rest.

# %%
# Create an empty dataframe with the required columns
addition_df = pd.DataFrame(
    columns=["Prompt", "Activation Location", "Activation Name", "Magnitude"]
)

from algebraic_value_editing import prompt_utils

# Loop through activation locations and prompts
for act_loc in activation_locations:
    anger_calm_additions: List[RichPrompt] = [
        RichPrompt(prompt="Anger", coeff=5, act_name=act_loc), 
        RichPrompt(prompt="Calm", coeff=-5, act_name=act_loc)
    ]
    act_name: str = prompt_utils.get_block_name(block_num=act_loc)
    for addition in anger_calm_additions:
        mags: torch.Tensor = hook_utils.prompt_magnitudes(
            model=model, prompt=addition.prompt, act_name=act_name
        ).cpu()

        for pos, mag in enumerate(mags):
            # Create a new dataframe row with the current data
            row = pd.DataFrame(
                {
                    "Prompt": [f"{addition.prompt}, pos {pos}"],
                    "Activation Location": [act_loc],
                    "Activation Name": [act_name],
                    "Magnitude": [mag],
                }
            )

            # Append the new row to the dataframe
            addition_df = pd.concat([addition_df, row], ignore_index=True)

# %% Make a plotly line plot of the RichPrompt magnitudes

def line_plot(df: pd.DataFrame, log_y: bool = True, title: str = "ActivationAddition Prompt Magnitude by Layer Number", legend_title_text: str = "Prompt") -> go.Figure:
    """ Make a line plot of the RichPrompt magnitudes. """
    for col in ["Prompt", "Activation Location", "Magnitude"]:
        assert col in df.columns, f"Column {col} not in dataframe"

    if log_y:
        df["LogMagnitude"] = np.log10(df["Magnitude"])

    fig = px.line(df, x="Activation Location", y="LogMagnitude" if log_y else "Magnitude", color="Prompt", color_discrete_sequence=px.colors.sequential.Rainbow[::-1])

    # Add dots where the datapoints are 
    fig.update_traces(mode="markers+lines")

    fig.update_layout(legend_title_text=legend_title_text,
                        title=title,  
                        xaxis_title="Layer Number",
                        yaxis_title=f"Magnitude{' (log 10)' if log_y else ''}")

    return fig

fig: go.Figure = line_plot(addition_df)
fig.show()

# %% Now let's plot how the steering vector magnitudes change with layer
# number
steering_df = pd.DataFrame(
    columns=["Prompt", "Activation Location", "Activation Name", "Magnitude"]
)

for act_loc in activation_locations:
    anger_calm_additions: List[RichPrompt] = [
        RichPrompt(prompt="Anger", coeff=5, act_name=act_loc), 
        RichPrompt(prompt="Calm", coeff=-5, act_name=act_loc)
    ]

    mags: torch.Tensor = hook_utils.steering_vec_magnitudes(
        model=model, act_adds=anger_calm_additions
    ).cpu()
    
    prompt1_toks, prompt2_toks = [model.to_str_tokens(addition.prompt) for addition in anger_calm_additions]
    for pos, mag in enumerate(mags):    
        tok1, tok2 = prompt1_toks[pos], prompt2_toks[pos]    
        # Create a new dataframe row with the current data
        row = pd.DataFrame(
            {
                "Prompt": [f"{tok1}-{tok2}, pos {pos}"],
                "Activation Location": [act_loc],
                "Magnitude": [mag],
            }
        )

        # Append the new row to the dataframe   
        steering_df = pd.concat([steering_df, row], ignore_index=True)

# %% Make a plotly line plot of the steering vector magnitudes
fig: go.Figure = line_plot(steering_df)
fig.show()
# %% Let's plot the steering vector magnitudes against the prompt
# magnitudes
relative_df = pd.DataFrame(
    columns=["Prompt", "Activation Location", "Activation Name", "Magnitude"]
)

for act_loc in activation_locations:
    anger_adds: List[RichPrompt] = [
        RichPrompt(prompt="Anger", coeff=5, act_name=act_loc),
        RichPrompt(prompt="Calm", coeff=-5, act_name=act_loc)
    ]
    mags: torch.Tensor = hook_utils.steering_magnitudes_relative_to_prompt(
        model=model, prompt="I think you're a", act_adds=anger_adds
    ).cpu()

    prompt1_toks, prompt2_toks = [model.to_str_tokens(addition.prompt) for addition in anger_adds]
    for pos, mag in enumerate(mags):    
        tok1, tok2 = prompt1_toks[pos], prompt2_toks[pos]    
        # Create a new dataframe row with the current data
        row = pd.DataFrame(
            {
                "Prompt": [f"{tok1}-{tok2}, pos {pos}"],
                "Activation Location": [act_loc],
                "Magnitude": [mag],
            }
        )

        # Append the new row to the dataframe
        relative_df = pd.concat([relative_df, row], ignore_index=True)

# %% Make a plotly line plot of the relative steering vector magnitudes  
fig: go.Figure = line_plot(relative_df, log_y=False, legend_title_text="Residual stream", title="Positionwise Steering Vector Magnitude / Prompt Magnitude")
fig.update_layout(
    annotations=[
        go.layout.Annotation(
            text="Prompt: \"I think you're a\"",
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.11,
            y=1.015,  # Adjust this value to move the subtitle up or down
            xanchor="center",
            yanchor="bottom",
            font=dict(size=13)
        )
    ]
)
fig.show()
# %%
