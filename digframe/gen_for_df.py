import exifread
import datetime

def get_date(filename):
    with open(filename, 'rb') as f:
        tags=exifread.process_file(f, details=False)
    #
    created = tags.get('EXIF DateTimeOriginal', tags.get('EXIF DateTimeDigitized',None))
    dt = datetime.datetime.strptime(str(created),'%Y:%m:%d %X')
    yyyymmdd = dt.date().strftime('%Y%m%d')

    
    
