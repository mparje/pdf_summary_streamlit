import streamlit as st
from torch.utils import data
from transformers import pipeline

from PyPDF2 import PdfFileReader
from fpdf import FPDF
import docx2txt

import string
import base64

import nltk
#Stop words present in the library
stopwords = nltk.corpus.stopwords.words('english')

max = st.sidebar.slider('Select max words', 50, 500, step=10, value=150)
min = st.sidebar.slider('Select min words', 10, 450, step=10, value=50)


def remove_stopwords(text):
	output= [i for i in text if i not in stopwords]
	return output

#defining the function to remove punctuation
def remove_punctuation(text):
	punctuationfree="".join([i for i in text if i not in string.punctuation])
	return punctuationfree

def create_download_link(val, filename):
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download file</a>'

@st.cache(allow_output_mutation=True)
def load_summarizer():
	model = pipeline("summarization", device=0)
	return model


def generate_chunks(inp_str):
	max_chunk = 500
	inp_str = inp_str.replace('.', '.<eos>')
	inp_str = inp_str.replace('?', '?<eos>')
	inp_str = inp_str.replace('!', '!<eos>')
	
	sentences = inp_str.split('<eos>')
	current_chunk = 0 
	chunks = []
	for sentence in sentences:
		if len(chunks) == current_chunk + 1: 
			if len(chunks[current_chunk]) + len(sentence.split(' ')) <= max_chunk:
				chunks[current_chunk].extend(sentence.split(' '))
			else:
				current_chunk += 1
				chunks.append(sentence.split(' '))
		else:
			chunks.append(sentence.split(' '))

	for chunk_id in range(len(chunks)):
		chunks[chunk_id] = ' '.join(chunks[chunk_id])
	return chunks


def read_pdf(file):
	pdfReader = PdfFileReader(file)
	count = pdfReader.numPages
	all_page_text = ""
	summarized_text = ""

	for i in range(count):
		page = pdfReader.getPage(i)
		raw_text = page.extractText()

		# raw_text = remove_stopwords(raw_text)
		raw_text_preprocessed = remove_punctuation(raw_text)

		summarized_text = summarized_text + '\n\n\n' + "PAGE {}: ".format(i + 1) + text_summarizer(raw_text_preprocessed, i)
		all_page_text = all_page_text + '\n\n\n' + "PAGE {}: ".format(i + 1) + raw_text

	return all_page_text, summarized_text

def text_summarizer(raw_text, i):

	with st.spinner("Generating Summary [PAGE: {}] ...".format(i + 1)):
		if raw_text:
			chunks = generate_chunks(raw_text)
			res = summarizer(chunks,
							max_length=max, 
							min_length=min, 
							do_sample=False)
			text = ' '.join([summ['summary_text'] for summ in res])

		return text


summarizer = load_summarizer()
st.title("Summarize Text")

docx_file = st.file_uploader("Upload File", type=['txt','docx','pdf'])
if st.button("Process"):
	if docx_file is not None:
		file_details = {"Filename":docx_file.name,"FileType":docx_file.type,"FileSize":docx_file.size}
		st.write(file_details)

		# Check File Type
		if docx_file.type == "text/plain":

			st.text(str(docx_file.read(),"utf-8")) # empty
			raw_text = str(docx_file.read(),"utf-8") # works with st.text and st.write,used for futher processing
			st.text_area('Loaded from pdf: {}'.format(docx_file.name), value=raw_text, height=500, max_chars=None, key=None)

		elif docx_file.type == "application/pdf":

			raw_text, summarized_text = read_pdf(docx_file)

			st.text_area('Loaded from pdf: {}'.format(docx_file.name), value=raw_text, height=500, max_chars=None, key=None)
			st.text_area('Summarized Text: ', value=summarized_text, height=500, max_chars=None, key=None)

			st.download_button(label= "Export Report TXT", data= summarized_text, file_name='summarized_text_'+docx_file.name.split('.')[0] + '.txt', mime="text/plain")

			
			# try:

			# 	pdf = FPDF()
			# 	pdf.add_page()
			# 	pdf.set_font('Arial', 'B', 16)
			# 	# for x in summarized_text:
			# 	pdf.cell(200, 10, txt = summarized_text, ln = 1, align = 'C')

			# 	html = create_download_link(pdf.output(dest="S").encode("latin-1"), 'summarized_text_'+docx_file.name)
			# 	st.markdown(html, unsafe_allow_html=True)

			# except Exception as e:
			# 	print("Export Report ERROR: ", e)
			
		
		elif docx_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":

			# Use the right file processor ( Docx,Docx2Text,etc)
			raw_text = docx2txt.process(docx_file) # Parse in the uploadFile Class directory
			st.text_area('Loaded from pdf: {}'.format(docx_file.name), value=raw_text, height=500, max_chars=None, key=None)

