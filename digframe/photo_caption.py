#! /usr/bin/env python
# Add and/or burn caption JPEG image. 
# EXAMPLE:
#   photoCaption.py --loglevel=INFO -b --outdir withCaptions ForDad2013-c/*.jpg
#!   ./photoCaption.py -b --loglevel=DEBUG --defaultCaption="test caption to burn in" ~/Desktop/picts/*.jpg

import os, sys, string, argparse, logging
import Image, ImageDraw,  ImageFont, JpegImagePlugin, IptcImagePlugin
import shutil
import iptcinfo

jpg='/home/pothiers/Desktop/picts-with-captions/y2007-P1210009.jpg'
def addCaption(jpgfile, outfile, burn=True, default=None):
    iptcLut = dict([(name,tag) for tag,name in iptcinfo.c_datasets.items()]) # name => tag
    orig = Image.open(jpgfile)
    #captionKey = (2,120) # called "description" in gThumb
    #info = IptcImagePlugin.getiptcinfo(orig)
    #!headlineKey = 105
    #!captionKey = 120
    info = None
    try:
        iptc = iptcinfo.IPTCInfo(jpgfile,
                                 force=True,
                                 reportScanError = False,
                                 )
        info = iptc.getData()
    except Exception:
        pass
    im = orig.copy()
    #orig.close()

    if not info:
        logging.debug('No IPTC header in: %s',jpgfile)
        caption = default
    else:
        caption = info.get(iptcLut['caption/abstract'],default)

    if caption == None: 
        logging.debug('No caption for: %s',jpgfile)
        return False
    logging.info('Caption of (%s): %s',jpgfile,caption)

    if burn:
        # Burn text at bottom/center of image 
        
        # NOTE: if image is much larger than digitial frame, most will
        # reduce image therby reducing caption size (possibly making
        # it too small to see clearly)

        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/arial.ttf',15)
        font = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',15)
        (textW, textH) = draw.textsize(caption,font=font)

        (width,height) = im.size
        #x = max(0,int(rond(width/2))-int(round(textW/2)))
        x = max(0,int(round((width-textW)/2)) )
        y = height-textH
        draw.rectangle([0,y-4,width,height],fill='gray')
        draw.text((x,y),caption,font=font,fill='cornsilk')
        
    im.save(outfile)
    #im.show()
    return True

def main():
    #print 'EXECUTING: %s\n\n' % (string.join(sys.argv))
    parser = argparse.ArgumentParser(
        version='1.0.1',
        description='Add or burn caption into JPEG header/image.'
        ' This handles captions created by Picasa.',
        epilog='EXAMPLE: %(prog)s -b starred-files/*.jpg   # Burn existing JPEG caption (if any) into image'
        )
    parser.add_argument('infiles',  help='Input files (jpg)', nargs='+')
    parser.add_argument('--defaultCaption',  help='Caption to use when there is not one in the header',
                        default=None)
    parser.add_argument('--outdir',  help='Directory in which to write input files with burned in captions',
                        default='/tmp/captions')
    parser.add_argument('-b','--burn',  help='Burn existing caption (else "defaultCaption") into image',
                        default=False, const=True, action='store_const')    
    parser.add_argument('--loglevel',      help='Kind of diagnostic output',
                        choices = ['CRTICAL','ERROR','WARNING','INFO','DEBUG'],
                        default='WARNING',
                        )
    args = parser.parse_args()

    #!print 'My args=',args
    #!print 'infile=',args.infile

    log_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(log_level, int):
        parser.error('Invalid log level: %s' % args.loglevel) 
    logging.basicConfig(level = log_level,
                        format='%(levelname)s %(message)s',
                        datefmt='%m-%d %H:%M'
                        )
    logging.debug('Debug output is enabled!!!')

    captionCnt = 0
    for infile in args.infiles:
        #!(r,ext) = os.path.splitext(infile)
        #!tempfile = '/tmp/caption'+ext
        #!print 'Captioning:',infile
        #!if addCaption(infile, tempfile, burn=args.burn, default=args.defaultCaption):
        #!    shutil.copyfile(tempfile,infile)

        base = os.path.basename(infile)
        outfile = os.path.join(args.outdir,base)
        if not addCaption(infile, outfile , burn=args.burn, default=args.defaultCaption):
            shutil.copyfile(infile,outfile)
        else:
            captionCnt += 1

    print 'Wrote captions to %d of %d files in: %s.'%(captionCnt, len(args.infiles), args.outdir)

if __name__ == '__main__':
    main()
    
