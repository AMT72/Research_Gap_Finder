"""
المرحلة الرابعة: توليد تقرير PDF احترافي
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ألوان المشروع
BLUE_DARK  = colors.HexColor("#0C447C")
BLUE_MID   = colors.HexColor("#185FA5")
BLUE_LIGHT = colors.HexColor("#E6F1FB")
TEAL       = colors.HexColor("#0F6E56")
TEAL_LIGHT = colors.HexColor("#E1F5EE")
AMBER      = colors.HexColor("#854F0B")
AMBER_LIGHT= colors.HexColor("#FAEEDA")
GRAY_DARK  = colors.HexColor("#444441")
GRAY_LIGHT = colors.HexColor("#F1EFE8")
WHITE      = colors.white


def build_styles():
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ReportTitle',
        fontSize=22,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    h1 = ParagraphStyle(
        'H1',
        fontSize=14,
        textColor=BLUE_DARK,
        spaceBefore=14,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    h2 = ParagraphStyle(
        'H2',
        fontSize=12,
        textColor=TEAL,
        spaceBefore=10,
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    body = ParagraphStyle(
        'Body',
        fontSize=10,
        textColor=GRAY_DARK,
        spaceAfter=4,
        leading=15,
        fontName='Helvetica'
    )
    small = ParagraphStyle(
        'Small',
        fontSize=9,
        textColor=colors.HexColor("#888780"),
        spaceAfter=2,
        fontName='Helvetica'
    )
    gap_style = ParagraphStyle(
        'Gap',
        fontSize=10,
        textColor=BLUE_DARK,
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=12,
        fontName='Helvetica-Bold'
    )
    idea_style = ParagraphStyle(
        'Idea',
        fontSize=10,
        textColor=TEAL,
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=12,
        fontName='Helvetica-Bold'
    )
    return {
        'title': title_style, 'h1': h1, 'h2': h2,
        'body': body, 'small': small, 'gap': gap_style, 'idea': idea_style
    }


def score_color(score: float):
    if score >= 8:
        return TEAL
    elif score >= 6:
        return BLUE_MID
    else:
        return AMBER


def generate_report(summaries: list[dict], gaps: dict) -> bytes:
    """توليد تقرير PDF كامل وإرجاعه كـ bytes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = build_styles()
    story = []

    # ─── غلاف ───
    story.append(Spacer(1, 1*cm))

    # صندوق العنوان
    cover_data = [[
        Paragraph("Research Gap Finder", styles['title']),
    ]]
    cover_table = Table(cover_data, colWidths=[17*cm])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BLUE_DARK),
        ('ROUNDEDCORNERS', [8]),
        ('TOPPADDING', (0,0), (-1,-1), 18),
        ('BOTTOMPADDING', (0,0), (-1,-1), 18),
        ('LEFTPADDING', (0,0), (-1,-1), 20),
        ('RIGHTPADDING', (0,0), (-1,-1), 20),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 0.4*cm))

    # معلومات التقرير
    date_str = datetime.now().strftime("%Y-%m-%d")
    meta = Table([
        [Paragraph(f"تاريخ التحليل: {date_str}", styles['small']),
         Paragraph(f"عدد الأوراق: {len(summaries)}", styles['small'])]
    ], colWidths=[8.5*cm, 8.5*cm])
    meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GRAY_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.6*cm))

    # ملخص عام
    if gaps.get("overall_summary"):
        story.append(HRFlowable(width="100%", thickness=0.5, color=BLUE_LIGHT))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("الملخص العام", styles['h1']))
        story.append(Paragraph(gaps["overall_summary"], styles['body']))
        story.append(Spacer(1, 0.3*cm))

    # ─── قسم 1: ملخصات الأوراق ───
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE_MID))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("1. ملخصات الأوراق البحثية", styles['h1']))
    story.append(Spacer(1, 0.2*cm))

    for i, s in enumerate(summaries, 1):
        title = s.get('title', s.get('filename', f'ورقة {i}'))
        items = [
            [Paragraph(f"#{i} — {title}", styles['h2'])],
        ]
        paper_block = Table(items, colWidths=[17*cm])
        paper_block.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), TEAL_LIGHT),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('ROUNDEDCORNERS', [4]),
        ]))
        story.append(KeepTogether([paper_block]))
        story.append(Spacer(1, 0.15*cm))

        # جدول تفاصيل الورقة
        details = [
            ["المشكلة", s.get('problem', '—')],
            ["الطريقة", s.get('method', '—')],
            ["البيانات", s.get('dataset', '—')],
            ["النتيجة", s.get('main_result', '—')],
            ["القيود", " | ".join(s.get('limitations', [])) or "—"],
        ]
        detail_table = Table(
            [[Paragraph(k, styles['small']), Paragraph(v, styles['body'])] for k, v in details],
            colWidths=[3*cm, 14*cm]
        )
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), GRAY_LIGHT),
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(detail_table)
        story.append(Spacer(1, 0.4*cm))

    # ─── قسم 2: Comparison Matrix ───
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE_MID))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("2. Comparison Matrix", styles['h1']))
    story.append(Spacer(1, 0.2*cm))

    matrix_headers = ["#", "الطريقة", "البيانات", "النتيجة"]
    matrix_data = [matrix_headers]
    for i, s in enumerate(summaries, 1):
        matrix_data.append([
            str(i),
            s.get('method', '—')[:40],
            s.get('dataset', '—')[:30],
            s.get('main_result', '—')[:40],
        ])

    matrix_table = Table(matrix_data, colWidths=[0.8*cm, 5.5*cm, 4.5*cm, 6.2*cm])
    matrix_style = [
        ('BACKGROUND', (0,0), (-1,0), BLUE_DARK),
        ('TEXTCOLOR', (0,0), (-1,0), WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]
    for row_idx in range(1, len(matrix_data), 2):
        matrix_style.append(('BACKGROUND', (0,row_idx), (-1,row_idx), BLUE_LIGHT))
    matrix_table.setStyle(TableStyle(matrix_style))
    story.append(matrix_table)
    story.append(Spacer(1, 0.5*cm))

    # ─── قسم 3: الأنماط الشائعة ───
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE_MID))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("3. الأنماط الشائعة في المجال", styles['h1']))

    def render_tag_list(items: list, color):
        if not items:
            return Paragraph("لا توجد بيانات", styles['body'])
        tags = "  ·  ".join(items)
        return Paragraph(tags, styles['body'])

    common_data = [
        [Paragraph("الطرق الشائعة", styles['h2']),
         Paragraph("البيانات الشائعة", styles['h2']),
         Paragraph("القيود الشائعة", styles['h2'])],
        [render_tag_list(gaps.get('common_methods', []), BLUE_MID),
         render_tag_list(gaps.get('common_datasets', []), TEAL),
         render_tag_list(gaps.get('common_limitations', []), AMBER)],
    ]
    common_table = Table(common_data, colWidths=[5.5*cm, 5.5*cm, 6*cm])
    common_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
        ('BACKGROUND', (0,0), (-1,0), GRAY_LIGHT),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(common_table)
    story.append(Spacer(1, 0.5*cm))

    # ─── قسم 4: Research Gaps ───
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE_MID))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("4. الثغرات البحثية المكتشفة", styles['h1']))
    story.append(Spacer(1, 0.2*cm))

    for i, gap in enumerate(gaps.get('research_gaps', []), 1):
        score = gap.get('novelty_score', 0)
        sc = score_color(score)

        gap_header = [[
            Paragraph(f"ثغرة #{i}", styles['gap']),
            Paragraph(f"Novelty: {score}/10", ParagraphStyle(
                'Score', fontSize=11, textColor=sc,
                alignment=TA_RIGHT, fontName='Helvetica-Bold'
            ))
        ]]
        gap_header_table = Table(gap_header, colWidths=[13*cm, 4*cm])
        gap_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), BLUE_LIGHT),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(gap_header_table)

        gap_detail = Table([
            [Paragraph("الثغرة:", styles['small']),
             Paragraph(gap.get('gap', '—'), styles['body'])],
            [Paragraph("الدليل:", styles['small']),
             Paragraph(gap.get('evidence', '—'), styles['body'])],
        ], colWidths=[2*cm, 15*cm])
        gap_detail.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(gap_detail)
        story.append(Spacer(1, 0.3*cm))

    # ─── قسم 5: أفكار بحثية مقترحة ───
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("5. الأفكار البحثية المقترحة", styles['h1']))
    story.append(Spacer(1, 0.2*cm))

    for i, idea in enumerate(gaps.get('suggested_ideas', []), 1):
        feasibility = idea.get('feasibility', '—')
        f_color = TEAL if 'عالية' in feasibility else (BLUE_MID if 'متوسطة' in feasibility else AMBER)

        idea_header = [[
            Paragraph(f"فكرة #{i}: {idea.get('idea', '—')}", styles['idea']),
        ]]
        idea_header_t = Table(idea_header, colWidths=[17*cm])
        idea_header_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), TEAL_LIGHT),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(idea_header_t)

        idea_detail = Table([
            [Paragraph("تعالج ثغرة:", styles['small']),
             Paragraph(idea.get('addresses_gap', '—'), styles['body'])],
            [Paragraph("الجدوى:", styles['small']),
             Paragraph(feasibility, ParagraphStyle('Feas', fontSize=10, textColor=f_color, fontName='Helvetica-Bold'))],
            [Paragraph("لماذا واعدة:", styles['small']),
             Paragraph(idea.get('why_promising', '—'), styles['body'])],
        ], colWidths=[2.5*cm, 14.5*cm])
        idea_detail.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor("#D3D1C7")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(idea_detail)
        story.append(Spacer(1, 0.35*cm))

    # ─── Footer ───
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_LIGHT))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"تم إنشاء هذا التقرير بواسطة Research Gap Finder — {date_str}",
        ParagraphStyle('Footer', fontSize=8, textColor=colors.HexColor("#888780"),
                       alignment=TA_CENTER, fontName='Helvetica')
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


if __name__ == "__main__":
    # اختبار التقرير بدون API
    test_summaries = [
        {
            "filename": "paper1.pdf",
            "title": "Car Damage Detection using CNN",
            "year": "2023",
            "authors": "Ahmed et al.",
            "problem": "Automatic detection of car body damage from images",
            "method": "ResNet-50 with transfer learning",
            "dataset": "CarDD Dataset (4000 images)",
            "main_result": "91% accuracy on test set",
            "limitations": ["Small dataset", "Only daylight images", "No video support"],
            "keywords": ["CNN", "damage", "car", "ResNet", "detection"],
            "status": "ok"
        },
        {
            "filename": "paper2.pdf",
            "title": "Insurance Claim Automation via Deep Learning",
            "year": "2022",
            "authors": "Wang et al.",
            "problem": "Automating insurance damage assessment",
            "method": "EfficientNet + severity classifier",
            "dataset": "Private insurance dataset",
            "main_result": "Reduces assessment time by 70%",
            "limitations": ["Private data not available", "English only", "No multilingual support"],
            "keywords": ["insurance", "EfficientNet", "severity", "automation"],
            "status": "ok"
        }
    ]
    test_gaps = {
        "status": "ok",
        "common_methods": ["CNN", "ResNet", "EfficientNet"],
        "common_datasets": ["CarDD", "Private datasets"],
        "common_limitations": ["Small datasets", "No video support", "English only"],
        "research_gaps": [
            {
                "gap": "لا توجد دراسات تدعم اللغة العربية في تقييم الأضرار",
                "evidence": "جميع الدراسات تستخدم English datasets فقط",
                "novelty_score": 9.0
            },
            {
                "gap": "غياب نماذج تعمل على الفيديو في الوقت الفعلي",
                "evidence": "كل الدراسات تعتمد على الصور الثابتة فقط",
                "novelty_score": 7.5
            }
        ],
        "suggested_ideas": [
            {
                "idea": "نظام تقييم أضرار السيارات باللغة العربية",
                "addresses_gap": "غياب دعم اللغة العربية",
                "feasibility": "عالية",
                "why_promising": "السوق العربي كبير وغير مغطى بحثياً"
            }
        ],
        "overall_summary": "المجال في نمو سريع مع تركيز على الصور الثابتة. الثغرة الأكبر هي دعم اللغات غير الإنجليزية والتحليل الفيديو."
    }

    pdf_bytes = generate_report(test_summaries, test_gaps)
    with open("/tmp/test_report.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"تم إنشاء التقرير: {len(pdf_bytes)} bytes")
