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
  # Screen-saver
  gen_for_df.py --width=1920 --height=1200 ~/Desktop/wilderness ~/Desktop/wilderness.1920

  # digitial frame NIX x15a 
  gen_for_df.py ~/Desktop/river-15 ~/Desktop/river.1024

TODO:
  - Truncate and report long captions. Total max chars=148.
    But write full captions to catalog.


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
    out = bytes.decode(subprocess.check_output(cmd.format(filename), shell=True))



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
                 caption='',
                 maxCapLen=148):
    #!print('EXECUTE burn_caption({}, {}, caption={}'
    #!      .format(outfile, digitizedDate,caption))

    im = Image.open(outfile)
    if digitizedDate and digitizedDate.year != 1900:
        if (caption == '' ):
            # use digitized date/time for caption
            caption = digitizedDate.strftime('%a %m/%d/%Y %M:%H:%S')
        else:
            # prepend digitized year to caption
            caption = '{}: {}'.format(digitizedDate.strftime('%m/%d/%y'), caption)
        
    # Burn text at bottom/center of image 
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(ttf,15)
    captxt = caption if len(caption) <= maxCapLen else caption[:maxCapLen-3]+'...'
    (textW, textH) = draw.textsize(captxt,font=font)

    (width,height) = im.size
    x = max(0,int(round((width-textW)/2)) )
    y = height-textH
    draw.rectangle([0,y-4,width,height],fill='gray')
    draw.text((x,y),captxt,font=font,fill='cornsilk')
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
                file_cnt += 1
                infile = os.path.join(root,fname)
                try:
                    md = get_metadata(infile)
                except Exception as ex:
                    print('WARNING: Could not read metadata from file "{}".\n{}'
                          .format(fname, ex))
                    continue
                except subprocess.CalledProcessError as cpe:
                    print('WARNING: Could not read metadata from file "{}". \n'
                          '  {} => {}\n  {}'
                          .format(fname, cmd, cpe.returncode, cpe.output))
                    continue

                if verbose:
                    print('[{}] Write record for {} to {}'
                          .format(file_cnt,fname,cname))
                write_catalog_rec(md, fname, root, catalog_file)
                
def burn_dir(indir, outdir, catalog_file, date_in_caption,
                      # for digitial frame with 4:3 aspect ratio
                      target_width=800, target_height=600, 
                      tolerance=0.01):
    goalAspect = float(target_width)/target_height
    bad_aspect_files = dict() # d[filename] => aspect
    bad_metadata_files = set()
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
                try:
                    md = get_metadata(os.path.join(root,fname))
                except Exception as ex:
                    print('ERROR: Could not read metadata from file "{}". SKIPPING\n{}'
                          .format(fname, ex))
                    bad_metadata_files.add(fname)
                    continue

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
        print('Bad aspect in {} files. All written anyhow. '
              'Goal aspect={} tolerance={}'
              .format(len(bad_aspect_files), goalAspect, tolerance))
        print('Diff\tAct\tFilename')
        for f,a in bad_aspect_files.items():
            print('  {0:.3f}\t{1:.3f}\t{2}'.format(abs(a-goalAspect),a,f))
                
    if len(bad_metadata_files) > 0:
        print('Bad metadata in {} files (they were skipped)'.format(len(bad_metadata_files)))
        print('\n'.join(bad_metadata_files))

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
                        #default=os.path.join(args.indir,'digitalframe-catalog.csv'),
                        type=argparse.FileType('w+'), )
    #!parser.add_argument('-d', '--date_in_caption',
    #!                    action='store_true',
    #!                    help='Include the date in the caption', )
    parser.add_argument('--no_date_in_caption',
                        action='store_true',
                        help='Do not include the date in the caption', )
    parser.add_argument('-j', '--just_catalog',
                        action='store_true',
                        help='Only write the catalog. Do not creates images.', )

    parser.add_argument('--height',
                        type=int, default=768,
                        help='Target output HEIGHT of images. NIX x15a is 1024x768.'
                        )
    parser.add_argument('--width',
                        type=int, default=1024,
                        help='Target output WIDTH of images. NIX x15a is 1024x768.'
                        )
                        
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
    if args.catalog_file == None:
        cfname = os.path.join(args.outdir,'digitalframe-catalog.csv')
        print('Writing catalog to: {}'.format(cfname))
        args.catalog_file = open(cfname, 'w+')
    if args.just_catalog:
        write_catalog(args.indir, args.catalog_file)
    else:
        burn_dir(args.indir, args.outdir,
                 args.catalog_file, not(args.no_date_in_caption),
                 target_width=args.width,
                 target_height=args.height   )
    print('Catalog written to: {}'.format(args.catalog_file.name))
if __name__ == '__main__':
    main()
