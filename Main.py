!pip install PyMuPDF PyPDF2
!pip install --upgrade PyMuPDF

import PyPDF2
from IPython.display import display, HTML, Javascript
import ipywidgets as widgets
import io
import re
from collections import defaultdict
import base64
import fitz  # PyMuPDF library

def extract_keywords(summary_text):
    words = re.findall(r'[\w\u0600-\u06FF]+', summary_text.lower())
    
    stop_words = {
        'the', 'and', 'of', 'in', 'to', 'a', 'is', 'that', 'for', 'it', 'as', 'was', 'be',
        'are', 'this', 'with', 'on', 'at', 'من', 'في', 'إلى', 'على', 'و', 'أو', 'أن'
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    return list(set(keywords))

def highlight_pdf(pdf_file, keywords, highlight_color):
    try:
        pdf_document = fitz.open(stream=pdf_file, filetype="pdf")
        
        color_map = {
            'أصفر': (1, 1, 0),
            'أحمر': (1, 0, 0),
            'أزرق': (0, 0, 1),
            'أخضر': (0, 1, 0),
            'وردي': (1, 0.75, 0.8),
            'سماوي': (0, 1, 1),
            'أرجواني': (0.5, 0, 0.5)
        }
        selected_color_rgb = color_map.get(highlight_color, (1, 1, 0))
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            existing_highlight_rects = []
            for annot in page.annots():
                if annot.type[0] == fitz.PDF_ANNOT_HIGHLIGHT:
                    existing_highlight_rects.append(annot.rect)
            
            for keyword in keywords:
                text_instances = page.search_for(keyword)
                
                for inst in text_instances:
                    is_already_highlighted = False
                    for existing_rect in existing_highlight_rects:
                        if inst.intersects(existing_rect):
                            is_already_highlighted = True
                            break
                    
                    if not is_already_highlighted:
                        highlight = page.add_highlight_annot(inst)
                        # هنا التعديل الصحيح: نستخدم set_colors لتعيين اللون
                        highlight.set_colors(stroke=selected_color_rgb)
                        # تحديث التعليق لحفظ التغييرات
                        highlight.update()
        
        output_pdf = io.BytesIO()
        pdf_document.save(output_pdf)
        pdf_document.close()
        output_pdf.seek(0)
        return output_pdf
    
    except Exception as e:
        print(f"حدث خطأ أثناء معالجة PDF: {str(e)}")
        return None

# واجهة المستخدم (الودجات)
# --------------------------------------------------------------------------------------------------

upload_pdf = widgets.FileUpload(
    description="رفع ملف PDF",
    accept='.pdf',
    style={'description_width': 'initial'}
)

summary_textarea = widgets.Textarea(
    placeholder='الصق نص الملخص هنا...',
    description='نص الملخص:',
    disabled=False,
    layout=widgets.Layout(width='80%', height='150px')
)

color_dropdown = widgets.Dropdown(
    options=['أصفر', 'أحمر', 'أزرق', 'أخضر', 'وردي', 'سماوي', 'أرجواني'],
    value='أصفر',
    description='اختر لون التظليل:',
    disabled=False,
    style={'description_width': 'initial'}
)

highlight_button = widgets.Button(
    description="تظليل الكلمات المطابقة",
    button_style='primary',
    icon='highlighter'
)

output = widgets.Output()

def on_upload_pdf(change):
    global uploaded_pdf
    uploaded_pdf = next(iter(change['new'].values()))['content']
    with output:
        print("✔ تم تحميل ملف PDF بنجاح")

def on_summary_change(change):
    global summary_text
    summary_text = change['new']
    if summary_text.strip() and 'uploaded_pdf' in globals():
        display(color_dropdown)
        display(highlight_button)

def download_file(filename, content):
    display(Javascript(f"""
    const element = document.createElement('a');
    element.setAttribute('href', 'data:application/pdf;base64,{content}');
    element.setAttribute('download', '{filename}');
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    """))

def on_highlight_clicked(b):
    if 'uploaded_pdf' not in globals() or 'summary_text' not in globals() or not summary_text.strip():
        with output:
            output.clear_output()
            print("⚠ يرجى تحميل ملف PDF وإدخال الملخص النصي أولاً")
        return
    
    with output:
        output.clear_output()
        print("⏳ جاري البحث عن الكلمات المطابقة وتظليلها...")
        
        try:
            keywords = extract_keywords(summary_text)
            if not keywords:
                print("⚠ لم يتم العثور على كلمات مناسبة في الملخص")
                return
            
            print(f"🔍 الكلمات التي سيتم تظليلها: {', '.join(keywords)}")
            
            highlight_color = color_dropdown.value
            highlighted_pdf = highlight_pdf(io.BytesIO(uploaded_pdf), keywords, highlight_color)
            
            if highlighted_pdf is None:
                print("❌ فشل في معالجة ملف PDF")
                return
            
            # تحويل PDF إلى base64 للتنزيل
            pdf_content = base64.b64encode(highlighted_pdf.getvalue()).decode('utf-8')
            
            # زر التنزيل
            download_button = widgets.Button(
                description="⬇ تنزيل PDF المظلل",
                button_style='success',
                icon='download'
            )
            
            def on_download_clicked(b):
                download_file('highlighted_document.pdf', pdf_content)
                with output:
                    print("✔ تم بدء تنزيل الملف")
            
            download_button.on_click(on_download_clicked)
            display(download_button)
            print("🎉 تم الانتهاء من التظليل بنجاح!")
        
        except Exception as e:
            print(f"❌ حدث خطأ: {str(e)}")

upload_pdf.observe(on_upload_pdf, names='value')
summary_textarea.observe(on_summary_change, names='value')
highlight_button.on_click(on_highlight_clicked)

# عرض واجهة المستخدم
display(HTML("<h2 style='text-align:center;color:#2e86c1'>أداة تظليل الكلمات المطابقة</h2>"))
display(HTML("<p style='text-align:center'>سيتم تظليل كل كلمة موجودة في الملخص وموجودة في PDF</p>"))

box_layout = widgets.Layout(display='flex', flex_flow='column', align_items='center', width='80%')
controls = widgets.VBox([upload_pdf, summary_textarea], layout=box_layout)
display(controls)
display(output)
