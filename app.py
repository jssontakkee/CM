import streamlit as st
import validators
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
# Corrected import for youtube-transcript-api exceptions (v1.0.3 uses NoTranscriptFound)
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re
import urllib3
import time
import random

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- IMPORTANT ---
# Replace with your actual Groq API key before deployment if needed
GROQ_API_KEY = "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" # Replace this with your actual API key

# --- Functions (extract_youtube_id, get_youtube_transcript - unchanged from previous version) ---
def extract_youtube_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_transcript(['en'])
            st.markdown("""<div class="success-message"><span>✅ Found English transcript!</span></div>""", unsafe_allow_html=True)
            fetched = transcript.fetch()
            return " ".join([t['text'] for t in fetched])
        except NoTranscriptFound:
            try:
                st.markdown("""<div class="info-message"><span>ℹ️ English transcript not available. Trying Hindi...</span></div>""", unsafe_allow_html=True)
                transcript = transcript_list.find_transcript(['hi'])
                st.markdown("""<div class="success-message"><span>✅ Found Hindi transcript!</span></div>""", unsafe_allow_html=True)
                st.markdown("""<div class="info-message"><span>⏳ Translating Hindi transcript to English...</span></div>""", unsafe_allow_html=True)
                translated_transcript = transcript.translate('en').fetch()
                st.markdown("""<div class="success-message"><span>✅ Translation complete!</span></div>""", unsafe_allow_html=True)
                return " ".join([t['text'] for t in translated_transcript])
            except NoTranscriptFound:
                st.markdown("""<div class="info-message"><span>ℹ️ Hindi transcript not available. Trying other languages...</span></div>""", unsafe_allow_html=True)
                available_languages = [t.language for t in transcript_list]
                st.markdown(f"""<div class="info-message"><span>ℹ️ Available languages: {', '.join(available_languages)}</span></div>""", unsafe_allow_html=True)
                try:
                    for available_transcript in transcript_list:
                        lang = available_transcript.language
                        lang_code = available_transcript.language_code
                        st.markdown(f"""<div class="info-message"><span>ℹ️ Found {lang} ({lang_code}) transcript. Processing...</span></div>""", unsafe_allow_html=True)
                        try:
                            if lang_code != 'en':
                                st.markdown(f"""<div class="info-message"><span>⏳ Translating {lang} transcript to English...</span></div>""", unsafe_allow_html=True)
                                translated = available_transcript.translate('en').fetch()
                                st.markdown("""<div class="success-message"><span>✅ Translation complete!</span></div>""", unsafe_allow_html=True)
                                return " ".join([t['text'] for t in translated])
                            else:
                                fetched = available_transcript.fetch()
                                return " ".join([t['text'] for t in fetched])
                        except Exception as lang_error:
                            st.markdown(f"""<div class="error-message"><span>⚠️ Error processing {lang} transcript: {str(lang_error)}. Trying next...</span></div>""", unsafe_allow_html=True)
                            continue
                    st.markdown("""<div class="error-message"><span>❌ No usable transcripts found after trying all available languages.</span></div>""", unsafe_allow_html=True)
                    return None
                except Exception as e:
                    st.markdown(f"""<div class="error-message"><span>❌ Error iterating through available transcripts: {str(e)}</span></div>""", unsafe_allow_html=True)
                    return None
    except TranscriptsDisabled:
        st.markdown("""<div class="error-message"><span>❌ Transcripts are disabled for this video.</span></div>""", unsafe_allow_html=True)
        return None
    except NoTranscriptFound:
         st.markdown("""<div class="error-message"><span>❌ No transcript was found for this video, even after checking available languages.</span></div>""", unsafe_allow_html=True)
         return None
    except Exception as e:
        if 'Could not retrieve a transcript for the video' in str(e) and 'YouTube is blocking requests from your IP' in str(e):
             st.markdown(f"""<div class="error-message"><span>❌ Failed to get YouTube transcript. YouTube is likely blocking requests from the server's IP address (common for cloud hosting). Website summarization should still work.</span><br><span>ℹ️ Error Detail: {e}</span></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="error-message"><span>❌ An unexpected error occurred while fetching transcripts: {str(e)}</span></div>""", unsafe_allow_html=True)
            if "For this video" in str(e):
                 error_msg = str(e)
                 available_langs = re.findall(r'\* ([a-z\-]+) \("([^"]+)"\)', error_msg)
                 if available_langs:
                     lang_codes = [code for code, name in available_langs]
                     st.markdown(f"""<div class="info-message"><span>ℹ️ Detected available language codes in error: {', '.join(lang_codes)}</span></div>""", unsafe_allow_html=True)
        return None


# Custom CSS to make the UI more modern with glassmorphic effect
st.set_page_config(
    page_title="Content Summarizer Pro",
    page_icon="📚",
    layout="wide",
)

# --- REVISED CSS ---
st.markdown("""
<style>
    /* Target the main app container for gradient background */
    [data-testid="stAppViewContainer"] > .main {
        background: linear-gradient(135deg, #8A2BE2, #FF69B4, #9370DB, #6A5ACD, #BA55D3);
        background-size: 300% 300%;
        animation: gradient 15s ease infinite;
    }

    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Floating gradient orbs (Targeting stAppViewContainer) */
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(255,105,180,0.8) 0%, rgba(255,105,180,0) 70%);
        top: -100px;
        left: 30%;
        border-radius: 50%;
        z-index: -1; /* Ensure it's behind content */
        animation: float 12s ease-in-out infinite;
    }

    [data-testid="stAppViewContainer"]::after {
        content: "";
        position: fixed;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(138,43,226,0.8) 0%, rgba(138,43,226,0) 70%);
        bottom: -150px;
        right: 20%;
        border-radius: 50%;
        z-index: -1; /* Ensure it's behind content */
        animation: float 15s ease-in-out infinite reverse;
    }

    @keyframes float {
        0% { transform: translate(0, 0); }
        50% { transform: translate(30px, 20px); }
        100% { transform: translate(0, 0); }
    }

    /* Glassmorphic effect for the main content block container */
    .main .block-container { /* This selector is usually reliable */
        padding-top: 2rem;
        padding-bottom: 2rem;
        backdrop-filter: blur(10px); /* Increased blur slightly */
        -webkit-backdrop-filter: blur(10px);
        background-color: rgba(255, 255, 255, 0.1); /* Slightly less opaque */
        border-radius: 16px;
        margin: 15px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }

    /* Other Glassmorphic elements (Cards, Expanders, etc.) */
    .card, .metric-card, .stExpander, .url-container, .summary-container {
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        background-color: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.18);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.3);
    }
    .metric-card { padding: 15px; text-align: center; }
    .stExpander { background-color: rgba(255, 255, 255, 0.1); padding: 0; } /* Adjust expander padding if needed */


    /* --- Summary Text Visibility Fix --- */
    .summary-container {
        background-color: rgba(249, 249, 249, 0.75); /* Made slightly more opaque */
        padding: 20px;
        border-radius: 16px;
        margin-top: 20px;
        color: black !important; /* APPLY BLACK COLOR TO THE CONTAINER ITSELF */
        backdrop-filter: blur(5px); /* Less blur for better readability maybe */
       -webkit-backdrop-filter: blur(5px);
    }
    /* Ensure specific elements inside inherit properly or are forced */
    .summary-container h3,
    .summary-container p,
    .summary-container li,
    .summary-container span,
    .summary-container div {
        color: black !important;
    }
    .summary-container hr {
        border-top: 1px solid rgba(0, 0, 0, 0.2);
    }
    .summary-container p[style*="text-align: right"] {
        color: #444 !important; /* Darker metadata text */
    }
    /* --- End Summary Fix --- */

    /* General Text Styling (Make default white for elements OUTSIDE summary) */
    body, .main, h1, h2, h4, h5, h6, label, .stMarkdown p, .stMarkdown li { /* Target more globally but avoid overriding summary */
        color: white;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
    }
     /* Ensure widget labels are white */
    label[data-testid="stWidgetLabel"] p {
        color: white !important;
         text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
    }
    /* Expander header text color */
    .stExpander > details > summary {
        color: white !important;
    }

    /* Input/Widget Styling (Mostly unchanged, ensure readability) */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {
        background-color: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: black !important; /* Input text black */
        border-radius: 10px;
        padding: 12px 15px; /* Adjust padding if needed */
        backdrop-filter: blur(5px);
    }
    .stTextInput > div > div > input::placeholder { color: rgba(0, 0, 0, 0.5); }
    .stSelectbox svg { fill: black !important; }
    div[data-baseweb="popover"] ul li { color: black !important; background-color: rgba(255, 255, 255, 0.95) !important; }
    div[data-baseweb="popover"] ul li:hover { background-color: rgba(220, 220, 220, 0.95) !important; }

    /* Button Styling (Unchanged) */
    div.stButton > button:first-child { /* ... */ }
    div.stButton > button:hover { /* ... */ }

    /* Message Boxes (Unchanged, ensure text color contrasts background) */
    .success-message { background-color: rgba(223, 240, 216, 0.8); border-left: 5px solid #4CAF50; padding: 15px; border-radius: 5px; margin: 10px 0; backdrop-filter: blur(4px); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); color: #155724; }
    .error-message { background-color: rgba(248, 215, 218, 0.8); border-left: 5px solid #dc3545; padding: 15px; border-radius: 5px; margin: 10px 0; backdrop-filter: blur(4px); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); color: #721c24; }
    .info-message { background-color: rgba(209, 236, 241, 0.8); border-left: 5px solid #17a2b8; padding: 15px; border-radius: 5px; margin: 10px 0; backdrop-filter: blur(4px); box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); color: #0c5460; }
    .success-message span, .success-message b { color: #155724 !important; }
    .error-message span, .error-message b { color: #721c24 !important; }
    .info-message span, .info-message b { color: #0c5460 !important; }

    /* Other styles (Progress bar, Headers, etc. - Unchanged) */
     .progress-bar { /* ... */ }
     .progress { /* ... */ }
     .app-header { /* ... */ }
     .app-title { /* ... */ }
     .app-subtitle { /* ... */ }
     .youtube-video { /* ... */ }
     .metric-value { /* ... */ }
     .metric-label { /* ... */ }
     .content-preview { /* ... */ }
     .text-with-icon { /* ... */ }

</style>
""", unsafe_allow_html=True)


# --- App Header (unchanged) ---
st.markdown("""
<div class="app-header">
    <div class="app-title">✨ Content Summarizer </div>
    <div class="app-subtitle">Instantly summarize YouTube videos and website content</div>
</div>
""", unsafe_allow_html=True)

# --- Columns and Sidebar Widgets (unchanged) ---
col1, col2 = st.columns([3, 1])

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    model_name = st.selectbox("Model", ["gemma-7b-it", "llama3-8b-8192", "mixtral-8x7b-32768"], index=0, help="Select AI model")
    chain_type = st.selectbox("Summarization Method", ["map_reduce", "stuff", "refine"], index=0, help="Speed vs. comprehensiveness")
    max_tokens = st.slider("Summary Length (Max Tokens)", 300, 1200, 600, 100, help="Adjust summary detail")

    if max_tokens <= 400: summary_type, detail_level = "Concise", "Brief overview"
    elif max_tokens <= 800: summary_type, detail_level = "Balanced", "Moderate detail"
    else: summary_type, detail_level = "Detailed", "In-depth coverage"
    st.markdown(f"""<div class="info-message" style="background-color: rgba(209, 236, 241, 0.4);"><b style="color: white;">{summary_type} Summary</b><br><span style="color: white; opacity: 0.9;">{detail_level}</span></div>""", unsafe_allow_html=True)

    is_api_key_present = GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY_HERE"
    is_api_key_plausible = is_api_key_present and GROQ_API_KEY.startswith("gsk_")
    if not is_api_key_present: st.markdown("""<div class="error-message" style="background-color: rgba(248, 215, 218, 0.4);"><span style="font-weight: bold; color: white;">⚠️ API Key Missing</span><br><span style="color: white; opacity: 0.9;">Update GROQ_API_KEY variable</span></div>""", unsafe_allow_html=True)
    elif not is_api_key_plausible: st.markdown("""<div class="error-message" style="background-color: rgba(248, 215, 218, 0.4);"><span style="font-weight: bold; color: white;">⚠️ API Key Invalid Format</span><br><span style="color: white; opacity: 0.9;">Check GROQ_API_KEY format</span></div>""", unsafe_allow_html=True)
    else: st.markdown("""<div class="success-message" style="background-color: rgba(223, 240, 216, 0.4);"><span style="font-weight: bold; color: white;">✅ API Ready</span><br><span style="color: white; opacity: 0.9;">Groq API key configured</span></div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""<div class="card"><h4>💡 Tips</h4><ul><li><b>YouTube:</b> May fail on cloud hosting due to IP blocks.</li><li><b>Websites:</b> Best for articles, blogs.</li><li><b>Map-reduce:</b> Good for long content.</li><li><b>Stuff:</b> Fastest for short content.</li><li><b>Refine:</b> Balanced accuracy.</li></ul></div>""", unsafe_allow_html=True)

# --- Main Content Area (unchanged logic, relies on CSS fixes) ---
with col1:
    st.markdown('<div class="url-container">', unsafe_allow_html=True)
    url_placeholder = "Enter YouTube URL or website URL..."
    url = st.text_input("", placeholder=url_placeholder, label_visibility="collapsed")

    if url:
        if validators.url(url):
            is_youtube = "youtube" in url or "youtu.be" in url
            if is_youtube:
                icon, url_type = "🎬", "YouTube Video"
                video_id = extract_youtube_id(url)
                if video_id:
                    st.markdown(f"""<div class="success-message"><div class="text-with-icon"><span>{icon} Valid {url_type} URL detected</span></div></div><iframe class="youtube-video" width="100%" height="450" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>""", unsafe_allow_html=True)
                else: st.markdown("""<div class="error-message"><span>⚠️ Could not extract YouTube video ID</span></div>""", unsafe_allow_html=True)
            else:
                icon, url_type = "🌐", "Website"
                st.markdown(f"""<div class="success-message"><div class="text-with-icon"><span>{icon} Valid {url_type} URL detected</span></div></div>""", unsafe_allow_html=True)
        else: st.markdown("""<div class="error-message"><span>⚠️ Invalid URL format</span></div>""", unsafe_allow_html=True)

    summarize_button = st.button("Summarize Content ✨", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Prompts based on max_tokens (unchanged)
    if max_tokens <= 400: map_template, combine_template = "Briefly summarize key points:\n\n{text}\n\nCONCISE SUMMARY:", "Combine summaries into 2-3 sentences:\n\n{text}\n\nFINAL CONCISE SUMMARY:"
    elif max_tokens <= 800: map_template, combine_template = "Summarize main ideas & details:\n\n{text}\n\nBALANCED SUMMARY:", "Create comprehensive summary:\n\n{text}\n\nFINAL BALANCED SUMMARY:"
    else: map_template, combine_template = "Detailed summary with examples/arguments:\n\n{text}\n\nDETAILED SUMMARY:", "Synthesize into in-depth summary:\n\n{text}\n\nFINAL DETAILED SUMMARY:"
    map_prompt = PromptTemplate(template=map_template, input_variables=["text"])
    combine_prompt = PromptTemplate(template=combine_template, input_variables=["text"])

    if summarize_button:
        is_api_key_present = GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY_HERE"
        is_api_key_plausible = is_api_key_present and GROQ_API_KEY.startswith("gsk_")
        if not is_api_key_present: st.markdown("""<div class="error-message"><span>⚠️ Update GROQ_API_KEY variable</span></div>""", unsafe_allow_html=True)
        elif not is_api_key_plausible: st.markdown("""<div class="error-message"><span>⚠️ API Key appears invalid</span></div>""", unsafe_allow_html=True)
        elif not url: st.markdown("""<div class="error-message"><span>⚠️ Please enter URL</span></div>""", unsafe_allow_html=True)
        elif not validators.url(url): st.markdown("""<div class="error-message"><span>⚠️ Invalid URL format</span></div>""", unsafe_allow_html=True)
        else:
            result_area = st.container()
            with result_area:
                st.markdown("""<div class="info-message"><span>⏳ Starting...</span></div><div class="progress-bar"><div class="progress" style="width: 5%;"></div></div>""", unsafe_allow_html=True)
                progress_bar = st.empty()
                try:
                    progress_bar.markdown("""<div class="info-message"><span>🔄 Initializing AI ({model_name})...</span></div><div class="progress-bar"><div class="progress" style="width: 15%;"></div></div>""", unsafe_allow_html=True)
                    time.sleep(0.5)
                    llm = ChatGroq(model=model_name, groq_api_key=GROQ_API_KEY, max_tokens=max_tokens)

                    is_youtube = "youtube" in url or "youtu.be" in url
                    docs = None
                    if is_youtube:
                        progress_bar.markdown("""<div class="info-message"><span>🎬 Processing YouTube...</span></div><div class="progress-bar"><div class="progress" style="width: 30%;"></div></div>""", unsafe_allow_html=True)
                        video_id = extract_youtube_id(url)
                        if not video_id: st.markdown("""<div class="error-message"><span>⚠️ No YouTube ID</span></div>""", unsafe_allow_html=True); st.stop()
                        transcript = get_youtube_transcript(video_id)
                        if transcript:
                            progress_bar.markdown(f"""<div class="success-message"><span>✅ Transcript: {len(transcript):,} chars</span></div><div class="progress-bar"><div class="progress" style="width: 45%;"></div></div>""", unsafe_allow_html=True)
                            docs = [Document(page_content=transcript, metadata={"source": url})]
                        else: st.stop() # Error shown in get_youtube_transcript
                    else: # Website
                        progress_bar.markdown("""<div class="info-message"><span>🌐 Loading Website...</span></div><div class="progress-bar"><div class="progress" style="width: 30%;"></div></div>""", unsafe_allow_html=True)
                        try:
                            loader = UnstructuredURLLoader(urls=[url], ssl_verify=False, headers={"User-Agent": "Mozilla/5.0"})
                            loaded_docs = loader.load()
                            if loaded_docs and loaded_docs[0].page_content:
                                docs = loaded_docs
                                total_chars_loaded = sum(len(d.page_content) for d in docs)
                                progress_bar.markdown(f"""<div class="success-message"><span>✅ Website Loaded: {len(docs)} element(s), {total_chars_loaded:,} chars</span></div><div class="progress-bar"><div class="progress" style="width: 45%;"></div></div>""", unsafe_allow_html=True)
                            else: st.markdown("""<div class="error-message"><span>❌ No content found/parsed</span></div>""", unsafe_allow_html=True); st.stop()
                        except Exception as e: st.markdown(f"""<div class="error-message"><span>❌ Error loading website: {e}</span></div>""", unsafe_allow_html=True); st.stop()

                    if docs:
                        progress_bar.markdown("""<div class="info-message"><span>🔄 Splitting text...</span></div><div class="progress-bar"><div class="progress" style="width: 60%;"></div></div>""", unsafe_allow_html=True)
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200)
                        split_docs = text_splitter.split_documents(docs)

                        col_a, col_b, col_c = st.columns(3)
                        character_count = sum(len(doc.page_content) for doc in split_docs)
                        word_count = sum(len(doc.page_content.split()) for doc in split_docs)
                        with col_a: st.markdown(f"""<div class="metric-card"><div class="metric-value">{len(split_docs)}</div><div class="metric-label">Chunks</div></div>""", unsafe_allow_html=True)
                        with col_b: st.markdown(f"""<div class="metric-card"><div class="metric-value">{character_count:,}</div><div class="metric-label">Characters</div></div>""", unsafe_allow_html=True)
                        with col_c: st.markdown(f"""<div class="metric-card"><div class="metric-value">{word_count:,}</div><div class="metric-label">Words</div></div>""", unsafe_allow_html=True)

                        with st.expander("📄 Content Preview (First 500 Chars)"):
                             st.markdown('<div class="content-preview">', unsafe_allow_html=True)
                             preview_text = docs[0].page_content[:500]
                             st.text(preview_text + "..." if len(docs[0].page_content) > 500 else preview_text)
                             st.markdown('</div>', unsafe_allow_html=True)
                        progress_bar.markdown("""<div class="progress-bar"><div class="progress" style="width: 70%;"></div></div>""", unsafe_allow_html=True)

                        progress_bar.markdown(f"""<div class="info-message"><span>🧠 Generating summary ('{chain_type}')...</span></div><div class="progress-bar"><div class="progress" style="width: 80%;"></div></div>""", unsafe_allow_html=True)

                        if chain_type == "map_reduce": chain = load_summarize_chain(llm, chain_type="map_reduce", map_prompt=map_prompt, combine_prompt=combine_prompt, verbose=False)
                        elif chain_type == "stuff":
                            total_chars = sum(len(d.page_content) for d in split_docs); est_tokens = total_chars / 4
                            context_window = 8192 if model_name == "llama3-8b-8192" else 32768 if model_name == "mixtral-8x7b-32768" else 8192
                            if est_tokens > (context_window * 0.85): st.warning(f"Content (~{est_tokens:.0f} tokens) may be too long for 'stuff' with {model_name} (~{context_window}). Try map_reduce/refine.")
                            chain = load_summarize_chain(llm, chain_type="stuff", prompt=map_prompt, verbose=False)
                        else: chain = load_summarize_chain(llm, chain_type="refine", question_prompt=map_prompt, refine_prompt=combine_prompt, verbose=False)

                        try:
                            with st.spinner(f"🤖 AI ({model_name}) working..."):
                                start_time = time.time()
                                result = chain.invoke({"input_documents": split_docs})
                                end_time = time.time(); summary_time_taken = end_time - start_time

                            progress_bar.markdown(f"""<div class="success-message"><span>✅ Summary Complete! ({summary_time_taken:.2f}s)</span></div><div class="progress-bar"><div class="progress" style="width: 100%;"></div></div>""", unsafe_allow_html=True)

                            st.markdown('<div class="summary-container">', unsafe_allow_html=True)
                            st.subheader("📝 Generated Summary")
                            st.markdown(result["output_text"]) # Display summary

                            summary_word_count = len(result["output_text"].split())
                            gen_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                            content_type_display = "YouTube" if is_youtube else "Website"
                            st.markdown(f"""<hr><p style="text-align: right; font-size: 0.9rem;">~{summary_word_count} words | {content_type_display} | {model_name} | {chain_type} | Max Tok: {max_tokens} | Gen: {gen_time_str}</p>""", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

                        except Exception as e: st.markdown(f"""<div class="error-message"><span>❌ Summarization failed: {e}</span></div>""", unsafe_allow_html=True); st.error("Suggestions: Try different model/method/length.")
                except Exception as e: st.markdown(f"""<div class="error-message"><span>❌ Unexpected setup error: {e}</span></div>""", unsafe_allow_html=True)
