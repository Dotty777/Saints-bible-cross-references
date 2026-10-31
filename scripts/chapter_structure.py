"""Count native chapters without moving the edition's original source sections."""
def chapter_units(data):
    groups={}
    for section in data['chapters']:
        groups.setdefault(section['chapter'],[]).extend(section['verses'])
    return groups

def completed_chapter_numbers(data):
    return [number for number,units in chapter_units(data).items()
            if units and all(v['status']=='completed' for v in units)]

def completed_source_sections(data):
    return [section.get('source_metadata',{}).get('section',index)
            for index,section in enumerate(data['chapters'],1)
            if section['verses'] and all(v['status']=='completed' for v in section['verses'])]

def chapter_references(data):
    return {str(number):[v['reference'] for v in units]
            for number,units in chapter_units(data).items()}
