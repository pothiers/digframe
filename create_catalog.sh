#!/bin/sh

# Speed: 65 files/minute

echo "Date, Caption, File, FullPath"
for jpgfile; do
    >&2 echo "Processing: $jpgfile"
    caption=`convert "${jpgfile}" 8BIMTEXT:- | grep -i caption  | cut -d = -f 2`
    date=`identify -format '%[EXIF:*]' "${jpgfile}" | grep -i DateTimeOriginal | cut -d = -f 2`
    file=`basename ${jpgfile} .JPG`
    echo "$date, $caption, \"$file\", \"$jpgfile\""
done
