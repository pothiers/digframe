#! /usr/bin/env python3
'''Use metadata from JPEG files to modify filename and image content
to make images more suitable for Digital Frame or screensaver.
Resulting filenames will sort alphabetically so they are in ascending datetime (of digitizing) order.
Resulting images will contain:
- Year digitized
- Caption (if one exists, can be added with Picasa)

Along the way, create a catalog containing:
date, caption, filename

EXAMPLES:
  gen_for_df.py --help ~/Desktop/river-15 ~/Desktop/river.1024

'''

import sys
import string
import argparse
import logging
import os
from glob import glob

import datetime as dt
import subprocess
from  PIL import Image, ImageDraw,  ImageFont


def get_metadata(filename):
    cmd=(R'identify -format "dict('
         'width=%w, height=%h, '
         'caption=###%[IPTC:2:120]###, '
         'date=\\"%[EXIF:DateTimeDigitized]\\" )" "{}"')
    #!print('DBG-1: filename={}, cmd={}'.format(filename, cmd))
    out = bytes.decode(subprocess.check_output(cmd.format(filename),
                                               shell=True))
    dictstr = out.replace("'","\\'").replace("###","'")
    #!print('DBG-2: out={}, dictstr={}'.format(out, dictstr))
    md = eval(dictstr)
    #!print('DBG-3: md={}'.format(md))
    
    # parse: 2007:11:21 11:27:06
    try:
        md['date'] = dt.datetime.strptime(md['date'],'%Y:%m:%d %H:%M:%S')
    except:
        md['date'] = dt.datetime(1900,1,1)
    return md

def burn_caption(outfile, digitizedDate,
                 ttf='/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',
                 caption=''):
    #!print('EXECUTE burn_caption({}, {}, caption={}'
    #!      .format(outfile, digitizedDate,caption))

    im = Image.open(outfile)
    if digitizedDate:
        if (caption == '' ):
            # use digitized date/time for caption
            caption = digitizedDate.strftime('%a %m/%d/%Y %M:%H:%S')
        else:
            # prepend digitized year to caption
            caption = '[{}] {}'.format(digitizedDate.year, caption)
        
    # Burn text at bottom/center of image 
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(ttf,15)
    (textW, textH) = draw.textsize(caption,font=font)

    (width,height) = im.size
    x = max(0,int(round((width-textW)/2)) )
    y = height-textH
    draw.rectangle([0,y-4,width,height],fill='gray')
    draw.text((x,y),caption,font=font,fill='cornsilk')
    im.save(outfile)

def write_catalog_rec(md, fname, root, catalog_file):
    print('{},"{}","{}","{}"'.format(md.get('date'),
                                     md.get('caption',''),
                                     fname,
                                     root),
          file=catalog_file)

def write_catalog(indir, catalog_file, verbose=True):
    file_cnt=1
    cname = catalog_file.name
    print('Date, Caption, File, FullPath', file=catalog_file)
    for root, dirs, files in os.walk(indir):
        for fname in files:
            if fname.lower().endswith('jpg'):
                infile = os.path.join(root,fname)
                md = get_metadata(infile)
                if verbose:
                    print('[{}] Write record for {} to {}'
                          .format(file_cnt,fname,cname))
                    file_cnt += 1
                write_catalog_rec(md, fname, root, catalog_file)
                
def burn_dir(indir, outdir, catalog_file, date_in_caption,
                      # for digitial frame with 4:3 aspect ratio
                      target_width=800, target_height=600, 
                      tolerance=0.01):
    goalAspect = float(target_width)/target_height
    bad_aspect_files = dict() # d[filename] => aspect
    file_cnt=0

    print('Date, Caption, File, FullPath', file=catalog_file)
    for root, dirs, files in os.walk(indir):
        for fname in files:
            if fname.lower().endswith('jpg'):
                file_cnt += 1
                xformbase = fname.replace(' ','_').replace('(Modified)','_modified_')
                pathname = os.path.join(outdir,'*T*-{}'.format(xformbase))
                if len(glob(pathname)) > 0:
                    print('[{}] Not replacing existing file: {}'
                          .format(file_cnt-1, os.path.join(outdir, xformbase)))
                    continue
                md = get_metadata(os.path.join(root,fname))
                stamp = md['date'].strftime('%Y%m%dT%H%M%S')
                newbase='{}-{}'.format(stamp, xformbase)
                newfile=os.path.join(outdir, newbase)
                #!if os.path.exists(newfile):
                #!    print('[{}] Not replacing existing file: {}'
                #!          .format(file_cnt-1, newfile))
                #!    continue

                infile = os.path.join(root,fname)

                write_catalog_rec(md, fname, root, catalog_file)

                thisAspect = float(md['width'])/md['height']
                if abs(thisAspect - goalAspect) > tolerance:
                    bad_aspect_files[infile] = thisAspect

                #######
                # make outfile fit desired aspect
                tmp1 = os.path.join('/tmp', newbase)                    
                cmd=('aspectpad -a {} -m l "{}" "{}"'
                     .format(float(target_width)/target_height, infile, tmp1))
                subprocess.check_output(cmd, shell=True)
                cmd=('convert "{}" -resize {}x{} "{}"'
                     .format(tmp1, target_width, target_height, newfile))
                subprocess.check_output(cmd, shell=True)

                digdate = md['date'] if date_in_caption else False
                burn_caption(newfile,  digdate, caption=md['caption'])
                print('[{}] Wrote file: {}'.format(file_cnt-1, newfile))

                
    # All done.  Report
    if len(bad_aspect_files) > 0:
        print('Bad aspect in (%d) files'.format(len(bad_aspect_files)))
        for f,a in bad_aspect_files.items():
            print('  {0:.3f}\t{1:.3f}\t{}'.format(abs(a-goalAspect),a,f))
                


##############################################################################

def main():
    #print('EXECUTING: {}\n\n'.format(' '.join(sys.argv)))
    parser = argparse.ArgumentParser(
        #!version='1.0.1',
        description='My shiny new python program',
        epilog='EXAMPLE: %(prog)s a b"'  )
    parser.add_argument('indir',
                        help='Use JPG descendants of this for input files.', )
    parser.add_argument('outdir',
                        help='Write modified files here.',  )
    parser.add_argument('-c', '--catalog_file', 
                        help='Output Catalog as CSV (else to STDOUT)',
                        default='digitalframe-catalog.csv',
                        type=argparse.FileType('w'), )
    parser.add_argument('-d', '--date_in_caption',
                        action='store_true',
                        help='Including the date in the caption', )
    parser.add_argument('-j', '--just_catalog',
                        action='store_true',
                        help='Only write the catalog. Do not creates images.', )

    parser.add_argument('--loglevel',      help='Kind of diagnostic output',
                        choices = ['CRTICAL','ERROR','WARNING','INFO','DEBUG'],
                        default='WARNING', )
    args = parser.parse_args()


    log_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(log_level, int):
        parser.error('Invalid log level: %s' % args.loglevel) 
    logging.basicConfig(level = log_level,
                        format='%(levelname)s %(message)s',
                        datefmt='%m-%d %H:%M'
                        )
    logging.debug('Debug output is enabled!!!')

    if args.just_catalog:
        write_catalog(args.indir, args.catalog_file)
    else:
        burn_dir(args.indir, args.outdir,
                 args.catalog_file, args.date_in_caption)
    print('Catalog written to: {}'.format(args.catalog_file.name))
if __name__ == '__main__':
    main()
