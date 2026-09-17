#!/usr/bin/env python3
"""
build_markdown.py
Final refined pipeline to convert full_bbox.xml into standard Markdown.
"""

import xml.etree.ElementTree as ET
import re
import unicodedata
import os
import sys

LIGATURES = {
    'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl',
    'ﬆ': 'st', 'ﬅ': 'ft'
}

def clean_text(txt):
    if not txt: return ''
    for lig, rep in LIGATURES.items():
        txt = txt.replace(lig, rep)
    # Remove control characters except newline and tab
    txt = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', txt)
    return txt

def is_cjk(ch):
    if not ch: return False
    o = ord(ch)
    return (0x4e00 <= o <= 0x9fff or 0x3400 <= o <= 0x4dbf or 0x3000 <= o <= 0x303f or 0xff00 <= o <= 0xffef)

def join_line_words(words):
    res = ''
    prev_xmax = None
    for xmin, ymin, xmax, ymax, txt in words:
        if not txt:
            continue
        is_fn = txt.isdigit() and (ymax - ymin) <= 7.0
        word_token = f"[^{txt}]" if is_fn else txt

        if prev_xmax is None:
            res = word_token
        else:
            dx = xmin - prev_xmax
            if is_fn:
                res += word_token
            elif res and is_cjk(res[-1]) and is_cjk(word_token[0]):
                res += word_token
            elif dx <= 0.8:
                res += word_token
            elif word_token in (',', '.', ';', ':', '!', '?', ')', '’', '”', '…') and dx < 1.5:
                res += word_token
            elif res.endswith(('(', '“', '‘')) and dx < 1.5:
                res += word_token
            else:
                res += ' ' + word_token
        prev_xmax = xmax
    return res

def group_words_into_lines(words):
    if not words:
        return []
    words.sort(key=lambda w: (w[1], w[0]))
    lines = []
    curr_line = []
    curr_y = None
    for w in words:
        if curr_y is None:
            curr_y = w[1]
            curr_line.append(w)
        elif abs(w[1] - curr_y) <= 3.2:
            curr_line.append(w)
        else:
            lines.append((curr_y, curr_line))
            curr_y = w[1]
            curr_line = [w]
    if curr_line:
        lines.append((curr_y, curr_line))

    line_data = []
    for y, lw in lines:
        lw.sort(key=lambda x: x[0])
        txt = join_line_words(lw)
        if txt.strip():
            line_data.append({
                'y': y,
                'x0': lw[0][0],
                'x1': lw[-1][2],
                'text': txt.strip()
            })
    return line_data

def unwrap_prose_lines(lines, base_x=None, indent_threshold=11.0, is_chinese=False):
    if not lines:
        return []

    if base_x is None:
        long_lines = [l for l in lines if len(l['text']) > 30]
        if long_lines:
            base_x = min(l['x0'] for l in long_lines)
        else:
            base_x = min(l['x0'] for l in lines)

    paragraphs = []
    curr_para = ""
    prev_line = None

    for l in lines:
        text = l['text']
        x0 = l['x0']
        y = l['y']

        is_new_para = False
        if prev_line is None:
            is_new_para = True
        else:
            dy = y - prev_line['y']
            if is_chinese:
                if prev_line['text'].endswith(('。', '！', '？', '」', '”')):
                    is_new_para = True
                elif dy > 16.0:
                    is_new_para = True
            else:
                if dy > 17.5:
                    is_new_para = True
                elif (x0 - base_x) >= indent_threshold and (prev_line['x0'] - base_x) < 4.0:
                    is_new_para = True
                elif text.startswith(('#', '##', '###', '####')):
                    is_new_para = True
                elif re.match(r'^(?:[ivxlcdm]+|[IVXLCDM]+)$', text):
                    is_new_para = True
                elif (x0 - base_x) >= 26.0 and len(text) < 45 and prev_line['x1'] < 330:
                    is_new_para = True

        if is_new_para:
            if curr_para:
                paragraphs.append(curr_para.strip())
            curr_para = text
        else:
            if curr_para.endswith('-') and not curr_para.endswith(('--', '—')):
                curr_para = curr_para[:-1] + text
            elif curr_para.endswith(('—', '--')):
                curr_para = curr_para + text
            elif is_chinese or (is_cjk(curr_para[-1]) and is_cjk(text[0])):
                curr_para = curr_para + text
            else:
                curr_para = curr_para + ' ' + text

        prev_line = l

    if curr_para:
        paragraphs.append(curr_para.strip())

    return paragraphs

def get_page_words(page, min_y=50, max_y=585, min_x=40, max_x=420, filter_margin_nums=False, is_recto=True):
    words = []
    ns = {'h': 'http://www.w3.org/1999/xhtml'}
    for w in page.findall('h:word', ns):
        txt = clean_text(''.join(w.itertext()).strip())
        if not txt: continue
        ymin = float(w.attrib['yMin'])
        ymax = float(w.attrib['yMax'])
        xmin = float(w.attrib['xMin'])
        xmax = float(w.attrib['xMax'])

        if ymin < min_y or ymax > max_y:
            continue
        if xmin < min_x or xmax > max_x:
            continue

        if filter_margin_nums:
            if is_recto and xmin >= 370 and txt.isdigit():
                continue
            if not is_recto and xmax <= 56 and txt.isdigit():
                continue

        words.append((xmin, ymin, xmax, ymax, txt))
    return words

def process_single_column_page(page, filter_margin_nums=False, is_recto=True, is_chinese=False):
    words = get_page_words(page, min_y=50, max_y=585, min_x=40, max_x=420,
                           filter_margin_nums=filter_margin_nums, is_recto=is_recto)
    lines = group_words_into_lines(words)
    return lines

def get_quote_boundary(words, page_num):
    if page_num in [344, 378, 379]:
        return 9999.0
    if page_num == 345:
        return 215.0

    straddles = [w for w in words if w[0] < 216.0 and w[2] > 216.0]
    if not straddles:
        return 0.0

    last_straddle_y = max(w[3] for w in straddles)

    words_below = [w for w in words if w[1] >= last_straddle_y - 2]
    words_below.sort(key=lambda w: (w[1], w[0]))
    raw_lines = []
    curr = []
    curr_y = None
    for w in words_below:
        if curr_y is None or abs(w[1] - curr_y) <= 3.2:
            curr.append(w)
            curr_y = w[1] if curr_y is None else curr_y
        else:
            raw_lines.append(curr)
            curr = [w]
            curr_y = w[1]
    if curr: raw_lines.append(curr)

    prev_y = last_straddle_y
    cut_y = last_straddle_y + 5.0
    for line in raw_lines:
        line_y = line[0][1]
        if line_y <= last_straddle_y:
            continue
        has_col2 = any(w[0] >= 216.0 for w in line)
        y_gap = line_y - prev_y
        if not has_col2 and y_gap < 18.0:
            prev_y = max(w[3] for w in line)
            cut_y = prev_y + 5.0
        else:
            break

    return cut_y

def process_commentary_page(page, page_num):
    """
    Process two-column Commentary page:
    Returns (top_lines, col1_lines, col2_lines)
    """
    words = get_page_words(page, min_y=50, max_y=585, min_x=40, max_x=420)
    if not words:
        return [], [], []

    cut_y = get_quote_boundary(words, page_num)
    if page_num == 345:
        top_words = [w for w in words if (w[1] + w[3]) / 2 >= cut_y]
        bot_words = [w for w in words if (w[1] + w[3]) / 2 < cut_y]
    elif cut_y == 0.0:
        top_words = []
        bot_words = words
    elif cut_y >= 9999.0:
        top_words = words
        bot_words = []
    else:
        top_words = [w for w in words if (w[1] + w[3]) / 2 < cut_y]
        bot_words = [w for w in words if (w[1] + w[3]) / 2 >= cut_y]

    # Gutter boundary at x = 216.0
    col1_words = [w for w in bot_words if w[0] < 216.0]
    col2_words = [w for w in bot_words if w[0] >= 216.0]

    top_lines = group_words_into_lines(top_words)
    col1_lines = group_words_into_lines(col1_words)
    col2_lines = group_words_into_lines(col2_words)

    return top_lines, col1_lines, col2_lines


def process_index_page(page):
    words = get_page_words(page, min_y=50, max_y=585, min_x=40, max_x=420)
    if not words:
        return [], []
    col1_words = [w for w in words if w[0] < 216.0]
    col2_words = [w for w in words if w[0] >= 216.0]
    col1_lines = group_words_into_lines(col1_words)
    col2_lines = group_words_into_lines(col2_words)
    return col1_lines, col2_lines

def process_personal_names_page(page, is_recto=True):
    words = get_page_words(page, min_y=52, max_y=585, min_x=40, max_x=420)
    if not words:
        return []

    if is_recto:
        c_cuts = [0, 135, 190, 290, 500]
    else:
        c_cuts = [0, 145, 200, 300, 500]

    words.sort(key=lambda w: (w[1], w[0]))
    line_groups = []
    curr_lg = []
    curr_y = None
    for w in words:
        if curr_y is None:
            curr_y = w[1]
            curr_lg.append(w)
        elif abs(w[1] - curr_y) <= 3.2:
            curr_lg.append(w)
        else:
            line_groups.append(curr_lg)
            curr_y = w[1]
            curr_lg = [w]
    if curr_lg:
        line_groups.append(curr_lg)

    table_rows = []
    for lg in line_groups:
        cols = ['', '', '', '']
        for w in lg:
            xmin = w[0]
            txt = w[4]
            for col_idx in range(4):
                if c_cuts[col_idx] <= xmin < c_cuts[col_idx+1]:
                    cols[col_idx] = (cols[col_idx] + ' ' + txt).strip()
                    break
        # Skip header and explanatory text
        if cols[0].lower().startswith(('pinyin', 'list of', 'the following', 'th e', 'introduction', 'ing to', 'giles')):
            continue
        if any(cols) and cols[0] and cols[1]:
            table_rows.append(f"| {cols[0]} | {cols[1]} | {cols[2]} | {cols[3]} |")

    return table_rows

def unwrap_column_blocks(blocks, indent_threshold=7.0):
    all_paras = []
    for lines in blocks:
        if not lines: continue
        paras = unwrap_prose_lines(lines, indent_threshold=indent_threshold)
        if not paras: continue

        if all_paras:
            prev = all_paras[-1]
            first = paras[0]
            if not prev.endswith(('.', '!', '?', '”', '’', ':', ';', '。', '」')) and not re.match(r'^(?:[ivxlcdm]+|[IVXLCDM]+)$', first) and not first.startswith(('#', '##', '###', '####')):
                if prev.endswith('-') and not prev.endswith(('--', '—')):
                    all_paras[-1] = prev[:-1] + first
                elif prev.endswith(('—', '--')):
                    all_paras[-1] = prev + first
                elif is_cjk(prev[-1]) and is_cjk(first[0]):
                    all_paras[-1] = prev + first
                else:
                    all_paras[-1] = prev + ' ' + first
                paras = paras[1:]

        all_paras.extend(paras)
    return all_paras

def main():
    print("Parsing full_bbox.xml...")
    tree = ET.parse('full_bbox.xml')
    ns = {'h': 'http://www.w3.org/1999/xhtml'}
    pages = tree.getroot().findall('.//h:page', ns)
    print(f"Loaded {len(pages)} pages.")

    doc = []

    # Title & Metadata
    doc.append("# The Record of Linji\n")
    doc.append("![Book Cover](images/cover.png)\n")
    doc.append("*Translation and Commentary by Ruth Fuller Sasaki*  \n*Edited by Thomas Yūhō Kirchner*  \n*Nanzan Library of Asian Religion and Culture*\n")

    # Front Matter
    print("Processing Front Matter...")
    doc.append("## Foreword")
    doc.append("*Yamada Mumon 山田無文*\n")
    fw_lines = []
    for p_idx in [7, 8]:
        is_recto = ((p_idx + 1) % 2 != 0)
        fw_lines.extend(process_single_column_page(pages[p_idx], is_recto=is_recto))

    fw_body = []
    editor_note = ""
    for l in fw_lines:
        if l['text'].startswith('Editor’s note:') or l['text'].startswith("Editor's note:"):
            editor_note = l['text']
        elif editor_note and len(l['text']) < 90 and not l['text'].endswith(('.', '”', '’')):
            editor_note += ' ' + l['text']
        else:
            fw_body.append(l)

    for p in unwrap_prose_lines(fw_body):
        if p.strip() and p not in ['Foreword', 'Yamada Mumon 山田無文']:
            doc.append(p + "\n")
    if editor_note:
        doc.append(f"> **{editor_note}**\n")

    # Preface to 1975 Edition (PDF pages 10-13)
    print("Processing Preface to 1975 Edition...")
    doc.append("## Preface to the 1975 Edition")
    doc.append("*Furuta Kazuhiro 古田和弘*\n")
    pref_lines = []
    for p_idx in range(9, 13):
        is_recto = ((p_idx + 1) % 2 != 0)
        pref_lines.extend(process_single_column_page(pages[p_idx], is_recto=is_recto))
    for p in unwrap_prose_lines(pref_lines):
        if p.strip() and p not in ['Preface to the 1975 Edition', 'Furuta Kazuhiro 古田和弘']:
            doc.append(p + "\n")

    # Editor's Prologue (PDF pages 14-31)
    print("Processing Editor's Prologue...")
    doc.append("## Editor’s Prologue")
    doc.append("*Thomas Yūhō Kirchner*\n")
    prologue_lines = []
    photo_caption = ""
    for p_idx in range(13, 31):
        pdf_page = p_idx + 1
        is_recto = ((p_idx + 1) % 2 != 0)
        p_lines = process_single_column_page(pages[p_idx], is_recto=is_recto)
        if pdf_page == 16:
            for l in p_lines:
                if l['y'] < 300:
                    photo_caption += ' ' + l['text']
                else:
                    prologue_lines.append(l)
        else:
            prologue_lines.extend(p_lines)

    for p in unwrap_prose_lines(prologue_lines):
        p_clean = p.strip()
        if not p_clean or p_clean == 'Editor’s Prologue':
            continue
        if p_clean.lower() == 'ruth fuller sasaki':
            if photo_caption:
                doc.append("\n![Photograph from 1 February 1955](images/ruth_fuller_sasaki_1955.png)")
                doc.append(f"*{photo_caption.strip()}*\n")
            doc.append("### Ruth Fuller Sasaki\n")
        elif p_clean.lower() == 'the 2008 edition':
            doc.append("\n### The 2008 Edition\n")
        elif p_clean.lower() == 'acknowledgments':
            doc.append("\n### Acknowledgments\n")
        else:
            doc.append(p_clean + "\n")

    # Abbreviations (PDF pages 32-33)
    print("Processing Abbreviations...")
    doc.append("## Abbreviations\n")
    abbr_lines = []
    for p_idx in range(31, 33):
        is_recto = ((p_idx + 1) % 2 != 0)
        abbr_lines.extend(process_single_column_page(pages[p_idx], is_recto=is_recto))
    for l in abbr_lines:
        if l['text'] != 'Abbreviations':
            doc.append(l['text'] + "\n")

    # Part 1: The Record of Linji (Translation)
    print("Processing Part 1: The Record of Linji...")
    doc.append("\n# Part 1: The Record of Linji")
    doc.append("*Translated by Ruth Fuller Sasaki*\n")

    # Discourses (PDF pages 36-66)
    print("Processing Discourses...")
    doc.append("## Discourses (上堂)\n")
    disc_lines = []
    for p_idx in range(35, 66):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0) # PDF 36 is recto (book p. 3)
        disc_lines.extend(process_single_column_page(pages[p_idx], filter_margin_nums=True, is_recto=is_recto))

    roman_pattern = re.compile(r'^(?:[ivxlcdm]+|[IVXLCDM]+)$')
    for p in unwrap_prose_lines(disc_lines):
        p_clean = p.strip()
        if p_clean in ['discourses', 'The Recorded Sayings of Chan Master Linji Huizhao of Zhenzhou', 'Compiled by his humble heir Huiran of Sansheng']:
            continue
        if roman_pattern.match(p_clean):
            doc.append(f"\n### Discourse {p_clean.upper()}\n")
        else:
            doc.append(p_clean + "\n")

    # Critical Examinations (PDF pages 67-74)
    print("Processing Critical Examinations...")
    doc.append("\n## Critical Examinations (勘辨)\n")
    crit_lines = []
    for p_idx in range(66, 74):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0)
        crit_lines.extend(process_single_column_page(pages[p_idx], filter_margin_nums=True, is_recto=is_recto))
    for p in unwrap_prose_lines(crit_lines):
        p_clean = p.strip()
        if p_clean.lower() in ['critical examinations', 'critical examinations 勘辨']:
            continue
        if roman_pattern.match(p_clean):
            doc.append(f"\n### Critical Examination {p_clean.upper()}\n")
        else:
            doc.append(p_clean + "\n")

    # Record of Pilgrimages (PDF pages 75-86)
    print("Processing Record of Pilgrimages...")
    doc.append("\n## Record of Pilgrimages (行錄)\n")
    pilg_lines = []
    for p_idx in range(74, 86):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0)
        pilg_lines.extend(process_single_column_page(pages[p_idx], filter_margin_nums=True, is_recto=is_recto))
    for p in unwrap_prose_lines(pilg_lines):
        p_clean = p.strip()
        if p_clean.lower() in ['record of pilgrimages', 'record of pilgrimages 行錄']:
            continue
        if roman_pattern.match(p_clean):
            doc.append(f"\n### Pilgrimage {p_clean.upper()}\n")
        else:
            doc.append(p_clean + "\n")

    # Preface of Ma Fang (PDF pages 87-89)
    print("Processing Preface of Ma Fang...")
    doc.append("\n## Preface to the Recorded Sayings of Chan Master Linji Huizhao of Zhenzhou")
    doc.append("*Ma Fang 馬防*\n")
    ma_lines = []
    for p_idx in range(86, 89):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0)
        ma_lines.extend(process_single_column_page(pages[p_idx], filter_margin_nums=True, is_recto=is_recto))
    for p in unwrap_prose_lines(ma_lines):
        p_clean = p.strip()
        if 'Preface to the Recorded Sayings' in p_clean or 'Ma Fang' in p_clean:
            continue
        doc.append(p_clean + "\n")

    # Part 2: Historical Introduction and Commentary
    print("Processing Part 2: Historical Introduction...")
    doc.append("\n# Part 2: Historical Introduction and Commentary\n")
    doc.append("## Historical Introduction to The Record of Linji")
    doc.append("*Yanagida Seizan 柳田聖山*\n")
    hist_lines = []
    for p_idx in range(90, 149):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0)
        hist_lines.extend(process_single_column_page(pages[p_idx], is_recto=is_recto))
    for p in unwrap_prose_lines(hist_lines):
        p_clean = p.strip()
        if p_clean in ['Historical Introduction', 'and Commentary', 'Historical Introduction to The Record of Linji', 'Yanagida Seizan']:
            continue
        if re.match(r'^\d+\.\s+[A-Z]', p_clean) and len(p_clean) < 70:
            doc.append(f"\n### {p_clean}\n")
        else:
            doc.append(p_clean + "\n")

    # Part 2: Commentary (PDF pages 150-379)
    print("Processing Commentary (two columns)...")
    doc.append("\n## Commentary")
    doc.append("*Ruth Fuller Sasaki*\n")

    current_commentary_sec = "Discourses"
    doc.append("### Commentary: Discourses\n")

    commentary_blocks = []
    for p_idx in range(149, 379):
        pdf_page = p_idx + 1
        top_lines, col1_lines, col2_lines = process_commentary_page(pages[p_idx], pdf_page)
        page_all_text = ' '.join(l['text'] for l in top_lines + col1_lines + col2_lines)

        # Check section transitions
        if 'critical examinations' in page_all_text.lower() and current_commentary_sec != "Critical Examinations" and p_idx >= 320:
            if commentary_blocks:
                for p in unwrap_column_blocks(commentary_blocks):
                    p_clean = p.strip()
                    if roman_pattern.match(p_clean):
                        doc.append(f"\n#### Commentary Section {p_clean.upper()}\n")
                    else:
                        doc.append(p_clean + "\n")
                commentary_blocks = []
            current_commentary_sec = "Critical Examinations"
            doc.append("\n### Commentary: Critical Examinations\n")
        elif 'preface to the recorded' in page_all_text.lower() and current_commentary_sec != "Preface" and p_idx >= 377:
            if commentary_blocks:
                for p in unwrap_column_blocks(commentary_blocks):
                    p_clean = p.strip()
                    if roman_pattern.match(p_clean):
                        doc.append(f"\n#### Commentary Section {p_clean.upper()}\n")
                    else:
                        doc.append(p_clean + "\n")
                commentary_blocks = []
            current_commentary_sec = "Preface"
            doc.append("\n### Commentary: Preface of Ma Fang\n")

        # Special order for page 345: top notes for Critical Examinations XXIV, then switch to Pilgrimages, then quote for Pilgrimage I
        if pdf_page == 345:
            if col1_lines: commentary_blocks.append(col1_lines)
            if col2_lines: commentary_blocks.append(col2_lines)
            if commentary_blocks:
                for p in unwrap_column_blocks(commentary_blocks):
                    p_clean = p.strip()
                    if roman_pattern.match(p_clean):
                        doc.append(f"\n#### Commentary Section {p_clean.upper()}\n")
                    else:
                        doc.append(p_clean + "\n")
                commentary_blocks = []
            current_commentary_sec = "Record of Pilgrimages"
            doc.append("\n### Commentary: Record of Pilgrimages\n")
            if top_lines:
                filt_top = [l for l in top_lines if l['text'] not in ['Commentary', 'discourses 上堂', 'discourses', 'critical examinations 勘辨', 'critical examinations', 'record of pilgrimages 行錄', 'record of pilgrimages']]
                if filt_top:
                    commentary_blocks.append(filt_top)
        else:
            if top_lines:
                filt_top = [l for l in top_lines if l['text'] not in ['Commentary', 'discourses 上堂', 'discourses', 'critical examinations 勘辨', 'critical examinations', 'record of pilgrimages 行錄', 'record of pilgrimages']]
                if filt_top:
                    commentary_blocks.append(filt_top)
            if col1_lines:
                commentary_blocks.append(col1_lines)
            if col2_lines:
                commentary_blocks.append(col2_lines)

    if commentary_blocks:
        for p in unwrap_column_blocks(commentary_blocks):
            p_clean = p.strip()
            if roman_pattern.match(p_clean):
                doc.append(f"\n#### Commentary Section {p_clean.upper()}\n")
            else:
                doc.append(p_clean + "\n")

    # Part 3: The Linji lu in Chinese
    print("Processing Chinese Text...")
    doc.append("\n# Part 3: The Linji lu in Chinese (臨濟錄)\n")
    zh_lines = []
    for p_idx in range(379, 397):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0)
        zh_lines.extend(process_single_column_page(pages[p_idx], is_recto=is_recto, is_chinese=True))
    for p in unwrap_prose_lines(zh_lines, is_chinese=True):
        p_clean = p.strip()
        if p_clean in ['Chinese Text', 'The Linji lu in Chinese']:
            continue
        if p_clean.lower() == 'discourses 上堂':
            doc.append("\n## Discourses 上堂\n")
        elif p_clean.lower() == 'critical examinations 勘辨':
            doc.append("\n## Critical Examinations 勘辨\n")
        elif p_clean.lower() == 'record of pilgrimages 行錄':
            doc.append("\n## Record of Pilgrimages 行錄\n")
        elif roman_pattern.match(p_clean):
            doc.append(f"\n### {p_clean.upper()}\n")
        else:
            doc.append(p_clean + "\n")

    # Part 4: Reference Matter
    print("Processing Reference Matter...")
    doc.append("\n# Part 4: Reference Matter\n")

    # Bibliography (PDF pages 398-469)
    print("Processing Bibliography...")
    doc.append("## Bibliography\n")
    bib_lines = []
    for p_idx in range(397, 469):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0)
        bib_lines.extend(process_single_column_page(pages[p_idx], is_recto=is_recto))
    for p in unwrap_prose_lines(bib_lines):
        p_clean = p.strip()
        if p_clean in ['Bibliography', 'principal sources', 'other sources']:
            if p_clean != 'Bibliography':
                doc.append(f"\n### {p_clean.title()}\n")
            continue
        doc.append(p_clean + "\n")

    # List of Personal Names (PDF pages 470-483)
    print("Processing List of Personal Names...")
    doc.append("\n## List of Personal Names\n")
    doc.append("The following list contains all Chinese names mentioned in the Historical Introduction and the Text and Commentary sections, arranged alphabetically according to their Chinese reading in Pinyin, followed by the Chinese characters, the Wade-Giles pronunciation, and the Japanese pronunciation.\n")
    doc.append("| Pinyin | Chinese | Wade-Giles | Japanese |")
    doc.append("|---|---|---|---|")
    for p_idx in range(469, 483):
        pdf_page = p_idx + 1
        is_recto = (pdf_page % 2 == 0)
        rows = process_personal_names_page(pages[p_idx], is_recto=is_recto)
        for r in rows:
            doc.append(r)
    doc.append("\n")

    # Cumulative Index (PDF pages 484-521)
    print("Processing Cumulative Index...")
    doc.append("## Cumulative Index\n")
    idx_blocks = []
    for p_idx in range(483, 521):
        c1, c2 = process_index_page(pages[p_idx])
        if c1: idx_blocks.append(c1)
        if c2: idx_blocks.append(c2)
    for p in unwrap_column_blocks(idx_blocks):
        p_clean = p.strip()
        if p_clean in ['Cumulative Index', 'Index']:
            continue
        doc.append(p_clean + "\n")

    final_text = "\n".join(doc)

    # Resolve hyphenated paragraph splits across columns/pages:
    def resolve_hyphen(m):
        w1 = m.group(1)
        w2 = m.group(2)
        if w1.lower() in ['consciousness', 'diamond']:
            return f'{w1}-{w2}'
        return f'{w1}{w2}'

    final_text = re.sub(r'(\b[a-zA-Z]{2,})-[ \t]*\n\n[ \t]*([a-zA-Z]{2,}\b)', resolve_hyphen, final_text)

    suspicious_fixes = [
        ('Intro duction', 'Introduction'),
        ('tradi- tional', 'traditional'),
        ('clas- sification', 'classification'),
        ('possi- ble', 'possible'),
        ('con- temporary', 'contemporary'),
        ('trans- lation', 'translation'),
        ('trans- lated', 'translated'),
        ('philo- sophical', 'philosophical'),
        ('apposi- Mazu', 'apposite Mazu'),
        ('c0mmentary', 'commentary'),
        ('noth208 ing', 'nothing'),
        ('noth208', 'nothing'),
        ('passion3.', 'passion 3.'),
        ('dis3.', 'distinct. 3.'),
        ('Th e ', 'The '),
    ]
    for old, new in suspicious_fixes:
        final_text = final_text.replace(old, new)

    # Re-insert hyphens into compound terms that lost them during soft-hyphen stripping
    compound_fixes = [
        (r'\bthoughtcreated\b', 'thought-created'),
        (r'\bthoughtinstant\b', 'thought-instant'),
        (r'\bmindground\b', 'mind-ground'),
        (r'\bMindground\b', 'Mind-ground'),
        (r'\bmindcreated\b', 'mind-created'),
        (r'\bselfnature\b', 'self-nature'),
        (r'\bselfnatured\b', 'self-natured'),
        (r'\bselfawaken\b', 'self-awaken'),
        (r'\bbuddhanature\b', 'buddha-nature'),
        (r'\bBuddhanature\b', 'Buddha-nature'),
        (r'\bdharmalike\b', 'dharma-like'),
        (r'\bdharmanatured\b', 'dharma-natured'),
        (r'\bDharmanatured\b', 'Dharma-natured'),
        (r'\bnonBuddhist\b', 'non-Buddhist'),
        (r'\bnonBuddhists\b', 'non-Buddhists'),
        (r'\bworldhonored\b', 'world-honored'),
        (r'\bWorldHonored\b', 'World-Honored'),
        (r'\btwelvefaced\b', 'twelve-faced'),
        (r'\bTwelvefaced\b', 'Twelve-faced'),
        (r'\btwelvelimbed\b', 'twelve-limbed'),
        (r'\bhelldwellers\b', 'hell-dwellers'),
        (r'\bkarmacreating\b', 'karma-creating'),
        (r'\bKarmacreating\b', 'Karma-creating'),
        (r'\bkarmanature\b', 'karma-nature'),
        (r'\bdungwiper\b', 'dung-wiper'),
        (r'\bearthshakings\b', 'earth-shakings'),
        (r'\bsensefields\b', 'sense-fields'),
        (r'\bricecook\b', 'rice-cook'),
        (r'\bwheelking\b', 'wheel-king'),
        (r'\bpatriarchbuddha\b', 'patriarch-buddha'),
        (r'\bpatriarchbuddhas\b', 'patriarch-buddhas'),
        (r'\bPatriarchbuddha\b', 'Patriarch-buddha'),
        (r'\brequitingbirth\b', 'requiting-birth'),
        (r'\bnotknowing\b', 'not-knowing'),
        (r'\babovementioned\b', 'above-mentioned'),
        (r'\ballembracing\b', 'all-embracing'),
        (r'\bbestknown\b', 'best-known'),
        (r'\bonepiece\b', 'one-piece'),
        (r'\bOnepiece\b', 'One-piece'),
        (r'\bfourcharacter\b', 'four-character'),
        (r'\bfivepart\b', 'five-part'),
        (r'\bFivepart\b', 'Five-part'),
        (r'\btensection\b', 'ten-section'),
        (r'\btenthousand\b', 'ten-thousand'),
        (r'\bsixthcentury\b', 'sixth-century'),
        (r'\btwentyfour\b', 'twenty-four'),
        (r'\bTwentyfour\b', 'Twenty-four'),
        (r'\bthirtytwo\b', 'thirty-two'),
        (r'\bthirtythree\b', 'thirty-three'),
        (r'\bthirtyfive\b', 'thirty-five'),
        (r'\bfiftytwo\b', 'fifty-two'),
        (r'\beightyone\b', 'eighty-one'),
        (r'\bConsciousnessonly\b', 'Consciousness-only'),
        (r'\bconsciousnessonly\b', 'consciousness-only'),
        (r'\bvicepresident\b', 'vice-president'),
    ]
    for pat, rep in compound_fixes:
        final_text = re.sub(pat, rep, final_text)

    output_path = "Record_of_Linji_Translation_&_Commentary_of_Ruth_Fuller_Sasaki_Thomas.md"
    print(f"Writing final Markdown to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"Done! Final output length: {len(final_text)} chars, {final_text.count(chr(10))} lines.")

if __name__ == '__main__':
    main()
