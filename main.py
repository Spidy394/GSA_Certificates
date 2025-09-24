import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
import fitz 
from PIL import Image

# Page Config
st.set_page_config(
    page_title="GSA-GCECT Certificate Download Portal", page_icon="🏆", layout="wide"
)

# Title and Desc.
st.title("🏆 GSA-GCECT Certificate Download Portal")
st.markdown("---")


@st.cache_data
def load_certificate_data():
    try:
        df = pd.read_csv("certificates.csv")
        return df
    except Exception:
        return pd.DataFrame()


def convert_drive_link_to_direct(drive_link):
    try:
        patterns = [
            r"/file/d/([a-zA-Z0-9-_]+)",
            r"id=([a-zA-Z0-9-_]+)",
            r"/d/([a-zA-Z0-9-_]+)",
        ]

        file_id = None
        for pattern in patterns:
            match = re.search(pattern, drive_link)
            if match:
                file_id = match.group(1)
                break

        if file_id:
            direct_link = f"https://drive.google.com/uc?export=download&id={file_id}"
            return direct_link, file_id
        else:
            return None, None

    except Exception:
        return None, None


@st.cache_data
def download_pdf_from_drive(drive_link):
    try:
        direct_link, file_id = convert_drive_link_to_direct(drive_link)
        if not direct_link:
            return None

        response = requests.get(direct_link, allow_redirects=True)

        if (
            response.status_code != 200
            or "content-type" in response.headers
            and "text/html" in response.headers["content-type"]
        ):
            direct_link = (
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm=1"
            )
            response = requests.get(direct_link, allow_redirects=True)

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "pdf" in content_type.lower() or response.content.startswith(b"%PDF"):
                return response.content
            else:
                return response.content  # Return anyway, assuming it's the file

        else:
            return None

    except Exception:
        return None


def display_pdf_preview(pdf_content, selected_name):
    with st.spinner("Loading certificate preview..."):
        try:
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")

            if pdf_document.page_count == 0:
                st.error("PDF appears to be empty")
                pdf_document.close()
                return

            page = pdf_document[0]

            pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))  # type: ignore

            img_data = pix.tobytes("png")
            image = Image.open(BytesIO(img_data))

            pdf_document.close()

            st.image(image, width="stretch")

        except Exception as e:
            st.error(f"Error displaying PDF preview: {str(e)}")
            st.info("You can still download the certificate using the button below.")


def main():
    df = load_certificate_data()

    if df.empty:
        st.error("No certificate data found. Please check your data file.")
        return

    # Create layout
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📋 Participants")

        names = df["Name"].tolist()

        selected_name = st.selectbox(
            "Choose your name from the list:",
            options=["Select your name..."] + names,
            index=0,
            help="Select your name to view and download your certificate",
        )

        if selected_name != "Select your name..." and selected_name in names:
            drive_link = df[df["Name"] == selected_name]["Drive_Link"].iloc[0]

            st.success("✅ Certificate found!")
            st.info(f"**Selected:** {selected_name}")

            if st.button("📩 Get Certificate", type="primary"):
                with st.spinner("Downloading certificate..."):
                    pdf_content = download_pdf_from_drive(drive_link)

                    if pdf_content:
                        st.session_state["pdf_content"] = pdf_content
                        st.session_state["selected_name"] = selected_name
                        st.success("✅ Certificate downloaded successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to download certificate.")
        else:
            if selected_name != "Select your name...":
                st.error("Name not found")
            st.info("👆 Please select your name from the dropdown first")

    with col2:
        st.subheader("📄 Certificate Preview")

        if (
            "pdf_content" in st.session_state
            and "selected_name" in st.session_state
            and st.session_state.get("selected_name") == selected_name
        ):
            display_pdf_preview(
                st.session_state["pdf_content"], st.session_state["selected_name"]
            )

            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                st.download_button(
                    label="📥 Download Certificate as PDF",
                    data=st.session_state["pdf_content"],
                    file_name=f"{st.session_state['selected_name'].replace(' ', '_')}_Certificate.pdf",
                    mime="application/pdf",
                    type="primary",
                    width="stretch",
                )

        else:
            st.markdown(
                """
            <div style="
                border: 2px dashed #ccc; 
                border-radius: 10px; 
                padding: 80px 20px; 
                text-align: center; 
                background: #f8f9fa;
                margin: 20px 0;
            ">
                <h3 style="color: #666; margin-bottom: 10px;">🏆 Certificate Preview</h3>
                <p style="color: #888; margin: 0;">Select your name and download to preview your certificate here</p>
            </div>
            """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
