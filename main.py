import flet as ft
import io
import re
from collections import defaultdict
import base64
import fitz  # PyMuPDF library

# (دوال extract_keywords و highlight_pdf تبقى كما هي)
def extract_keywords(summary_text):
    # ... نفس الكود السابق ...
    words = re.findall(r'[\w\u0600-\u06FF]+', summary_text.lower())
    
    stop_words = {
        'the', 'and', 'of', 'in', 'to', 'a', 'is', 'that', 'for', 'it', 'as', 'was', 'be',
        'are', 'this', 'with', 'on', 'at', 'من', 'في', 'إلى', 'على', 'و', 'أو', 'أن'
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    return list(set(keywords))

def highlight_pdf(pdf_file, keywords, highlight_color):
    # ... نفس الكود السابق ...
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

# دالة واجهة المستخدم الرئيسية في Flet
def main(page: ft.Page):
    page.title = "أداة تظليل الكلمات المطابقة"
    page.horizontal_alignment = "center"

    uploaded_pdf_content = None

    def on_file_pick(e: ft.FilePickerResultEvent):
        nonlocal uploaded_pdf_content
        if e.files:
            file = e.files[0]
            if file.name.endswith(".pdf"):
                uploaded_pdf_content = file.read()
                page.snack_bar = ft.SnackBar(ft.Text(f"✔ تم تحميل ملف PDF بنجاح"), open=True)
                summary_textarea.disabled = False
                highlight_button.disabled = False
            else:
                page.snack_bar = ft.SnackBar(ft.Text("⚠ يرجى اختيار ملف PDF"), open=True)
        page.update()

    file_picker = ft.FilePicker(on_result=on_file_pick)

    def on_highlight_clicked(e):
        if not uploaded_pdf_content or not summary_textarea.value.strip():
            page.snack_bar = ft.SnackBar(ft.Text("⚠ يرجى تحميل ملف PDF وإدخال الملخص النصي أولاً"), open=True)
            page.update()
            return
        
        page.snack_bar = ft.SnackBar(ft.Text("⏳ جاري البحث عن الكلمات المطابقة وتظليلها..."), open=True)
        page.update()

        try:
            keywords = extract_keywords(summary_textarea.value)
            if not keywords:
                page.snack_bar = ft.SnackBar(ft.Text("⚠ لم يتم العثور على كلمات مناسبة في الملخص"), open=True)
                page.update()
                return

            highlight_color = color_dropdown.value
            highlighted_pdf_stream = highlight_pdf(io.BytesIO(uploaded_pdf_content), keywords, highlight_color)
            
            if highlighted_pdf_stream is None:
                page.snack_bar = ft.SnackBar(ft.Text("❌ فشل في معالجة ملف PDF"), open=True)
                page.update()
                return
            
            # تحويل PDF إلى base64 للتنزيل
            pdf_content_base64 = base64.b64encode(highlighted_pdf_stream.getvalue()).decode('utf-8')
            
            # تنزيل الملف
            page.snack_bar = ft.SnackBar(ft.Text("🎉 تم الانتهاء من التظليل بنجاح!"), open=True)
            page.update()

            # إنشاء زر التنزيل
            download_button = ft.ElevatedButton(
                text="⬇ تنزيل PDF المظلل",
                icon=ft.icons.DOWNLOAD,
                on_click=lambda e: ft.web_launch_url(f"data:application/pdf;base64,{pdf_content_base64}"),
                style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE)
            )
            page.add(download_button)
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ حدث خطأ: {str(ex)}"), open=True)
            page.update()

    # إنشاء مكونات الواجهة باستخدام Flet
    upload_button = ft.ElevatedButton(
        "رفع ملف PDF",
        icon=ft.icons.UPLOAD_FILE,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"])
    )

    summary_textarea = ft.TextField(
        label='نص الملخص',
        hint_text='الصق نص الملخص هنا...',
        multiline=True,
        min_lines=5,
        max_lines=10
    )

    color_dropdown = ft.Dropdown(
        label="اختر لون التظليل",
        options=[
            ft.dropdown.Option("أصفر"),
            ft.dropdown.Option("أحمر"),
            ft.dropdown.Option("أزرق"),
            ft.dropdown.Option("أخضر"),
            ft.dropdown.Option("وردي"),
            ft.dropdown.Option("سماوي"),
            ft.dropdown.Option("أرجواني"),
        ],
        value="أصفر",
        width=200
    )

    highlight_button = ft.ElevatedButton(
        "تظليل الكلمات المطابقة",
        icon=ft.icons.HIGHLIGHT,
        on_click=on_highlight_clicked,
        bgcolor=ft.colors.BLUE_700,
        color=ft.colors.WHITE,
    )
    
    # عرض مكونات الواجهة
    page.add(
        ft.Text("أداة تظليل الكلمات المطابقة", size=24, weight="bold", text_align="center"),
        ft.Text("سيتم تظليل كل كلمة موجودة في الملخص وموجودة في PDF", size=14, text_align="center"),
        ft.Container(height=20),
        upload_button,
        summary_textarea,
        color_dropdown,
        highlight_button,
    )

if __name__ == "__main__":
    ft.app(target=main)

