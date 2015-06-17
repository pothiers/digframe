#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Add and/or burn caption JPEG image. 
# EXAMPLE:
#  For NIX x15a:
#  burn_captions.py --twidth=1024 --theight=768 --outdir starred.1024 starred/Starred_Photos/*.jpg
#
#  burn_captions.py --twidth=800 --theight=600 --outdir /media/FC30-3DA9/wilderness.800 /home/data/pictures-exported/hiking-starred/wilderness/*
#
#  burn_captions.py --twidth=800 --theight=600 --outdir ~/Desktop/picasa-export/test ~/Desktop/picasa-export/2013-07-17/*.JPG
#
#   burn_captions.py --rejectBadAspect --twidth=800 --theight=600 --burn --outdir ~/Desktop/picasa-export/test ~/Desktop/picasa-export/2013-07-17/*.JPG
#   burn_captions.py --only800x600 --burn --outdir ~/Desktop/picasa-export/burned-2013-07-17 ~/Desktop/picasa-export/2013-07-17/*.JPG146
#   burn_captions.py -b --only800x600 --outdir withCaptions ForDad2013-c/*.jpg
#   burn_captions.py --loglevel=INFO -b --outdir withCaptions ForDad2013-c/*.jpg
#   burn_captions.py -b --loglevel=DEBUG --defaultCaption="test caption to burn in" ~/Desktop/picts/*.jpg

import os, os.path, sys, string, argparse, logging, subprocess
import Image, ImageDraw,  ImageFont, JpegImagePlugin, IptcImagePlugin
import shutil
import iptcinfo


def burn_caption(outfile,
                 target_width=800, target_height=600, 
                 ttf='/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',
                 default=None):
    # name => tag
    iptcLut = dict([(name,tag) for tag,name in iptcinfo.c_datasets.items()]) 
    info = None
    try:
        #!print 'DBG-1'
        iptc = iptcinfo.IPTCInfo(outfile,
                                 force=True,
                                 reportScanError = False,
                                 inp_charset = None,
                                 )
        info = iptc.getData()
    except Exception:
        pass

    if not info:
        logging.debug('No IPTC header in: %s',outfile)
        caption = default
    else:
        caption = info.get(iptcLut['caption/abstract'],default)

    #! im = Image.open(outfile).resize((target_width,target_height),Image.ANTIALIAS)
    im = Image.open(outfile)
    if (caption != None): 
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


def addCaptionToFiles(infiles, outdir,
                      default=None,
                      # for digitial frame with 4:3 aspect ratio
                      target_width=800, target_height=600, 
                      tolerance=0.01,
                      ):
    goalAspect = float(target_width)/target_height
    fileCnt = 0
    totalFiles = len(infiles)
    bad_aspect_files = dict() # d[filename] => aspect

    for idx,infile in enumerate(infiles):
        print '%04d/%04d File="%s"'%(idx,totalFiles,infile)
        base = os.path.basename(infile).replace(' ','_').replace('(Modified)','_modified_')
        tmp1 = os.path.join('/tmp',base)
        outfile = os.path.join(outdir,base)
        if os.path.exists(outfile): continue

        # Track infiles that were bad aspect. Report later so I have option
        # to go back and hand crop them.
        cmd='identify -format "%%w %%h" "%s"'%(infile,)
        (width,height) = subprocess.check_output(cmd, shell=True).split()
        thisAspect = float(width)/float(height)
        if abs(thisAspect - goalAspect) > tolerance:
            bad_aspect_files[infile] = thisAspect

        # make outfile fit desired aspect
        cmd='aspectpad -a %s -m l "%s" "%s"'%(float(target_width)/target_height,
                                          infile, tmp1)
        output = subprocess.check_output(cmd, shell=True)
        #!print 'DBG: cmd="%s"'%(cmd,)
        #!cmd=('convert "%s" -gravity center -extent %sx%s "%s"'
        #!     %(tmp1, target_width, target_height, outfile))
        cmd=('convert "%s" -resize %sx%s "%s"'
             %(tmp1, target_width, target_height, outfile))
        #print 'DBG: cmd="%s"'%(cmd,)
        output = subprocess.check_output(cmd, shell=True)        
        #!os.remove(tmp1)
        
        burn_caption(outfile)
    # All done.  Report
    print 'Bad aspect in (%d) files'%(len(bad_aspect_files),)
    for f,a in bad_aspect_files.items():
        print '  %.3f\t%.3f\t%s'%(abs(a-goalAspect),a,f) 
        
        
                
        

jpg='/home/pothiers/Desktop/picts-with-captions/y2007-P1210009.jpg'
# RETURNS: True iff image was created in outfile.
def addCaption(jpgfile, outfile, 
               burn=True, 
               # for digitial frame with 4:3 aspect ratio
               target_width=800, target_height=600, 
               rejectBadAspect=True,
               #! only800x600=True, 
               default=None
               ):
    print 'Image File="%s"'%(jpgfile,)
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
    im.load()
    #orig.close()

    if not info:
        logging.debug('No IPTC header in: %s',jpgfile)
        caption = default
    else:
        caption = info.get(iptcLut['caption/abstract'],default)

    if caption == None: 
        logging.debug('No caption for: %s',jpgfile)
    else:
        logging.info('Caption of (%s): %s',jpgfile,caption)

    (width,height) = im.size
    logging.info('Width x Height = %d x %d'%(width,height))
    #!print ('Aspects: orig=%s, taget=%s'%(1.0*width/height,1.0*target_width/target_height))
    if abs(1.0*width/height - 1.0*target_width/target_height) > .01 :
        if rejectBadAspect:
            print ('Rejected image "%s"; bad aspect ratio. Expected %d:%d. Got %d:%d'
                   %(jpgfile,target_width, target_height,width,height))
            return False
        else:
            # convert image -gravity center -background white -extent 100x200% result
            # see http://www.imagemagick.org/Usage/crop/#extent
            print ('Distorting image "%s" with bad aspect ratio. Expected %d:%d(%4.3f). Got %d:%d(%4.3f)'
                   %(jpgfile,
                     target_width,target_height, float(target_width)/target_height,
                     width,height, float(width)/height,
                     ))
            
        
    if  (target_width > 0) and (width != target_width):
        print ('Resize image "%s"' % (jpgfile,))
        im2 = im.resize((target_width,target_height),Image.ANTIALIAS)
        im = im2


    if burn and (caption != None):
        # Burn text at bottom/center of image 
        # NOTE: if image is much larger than digitial frame, most will
        # reduce image therby reducing caption size (possibly making
        # it too small to see clearly)

        draw = ImageDraw.Draw(im)
        font = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/arial.ttf',15)
        font = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',15)
        (textW, textH) = draw.textsize(caption,font=font)

        (width,height) = im.size
        x = max(0,int(round((width-textW)/2)) )
        y = height-textH
        draw.rectangle([0,y-4,width,height],fill='gray')
        draw.text((x,y),caption,font=font,fill='cornsilk')
        print 'Burned caption: %s'%(caption,)

    im.save(outfile)
    return True

def main():
    #print 'EXECUTING: %s\n\n' % (string.join(sys.argv))
    parser = argparse.ArgumentParser(
        version='1.0.2',
        description='''Add or burn caption into JPEG header/image. 
This handles captions created by Picasa.''',
        epilog='''EXAMPLES: 
  %(prog)s --outdir wilderness.captions --burn --twidth 800 --theight 600 wilderness/*\n
  %(prog)s --twidth=800 --theight=600 --outdir /media/FC30-3DA9/wilderness.800 /home/data/pictures-exported/hiking-starred/wilderness/*
               '''
        )
    parser.add_argument('infiles',  help='Input files (jpg)', nargs='+')

    parser.add_argument('--outdir',  help='Directory in which to write input files with burned in captions',
                        default='/tmp/captions')
    parser.add_argument('--defaultCaption',  default=None,
                        help='Caption to use when there is not one in the header')
    parser.add_argument('-b','--burn',  action='store_true',
                        help='Burn existing caption (else "defaultCaption") into image')
    parser.add_argument('--twidth', type=int, default=800,
                        help='Desired (Target) output image width'
                        )
    parser.add_argument('--theight', type=int, default=600,
                        help='Desired (Target) output image height'
                        )
    parser.add_argument('--rejectBadAspect', action='store_true',
                        help='Do not copy image unless its aspect ratio is TWIDTH:THEIGHT)'
                        )

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

    #!fileCnt = 0
    #!totalFiles = len(args.infiles)
    #!for idx,infile in enumerate(args.infiles):
    #!    print '\nImage File="%s" (%d/%d)'%(infile,idx,totalFiles)
    #!    base = os.path.basename(infile)
    #!    outfile = os.path.join(args.outdir,base)
    #!    created =  addCaption(infile, outfile, 
    #!                          default=args.defaultCaption,
    #!                          burn=args.burn, 
    #!                          target_width=args.twidth,
    #!                          target_height=args.theight,
    #!                          rejectBadAspect = args.rejectBadAspect
    #!                          )
    #!    if created:
    #!        fileCnt += 1

    addCaptionToFiles(args.infiles, args.outdir, 
                      default=args.defaultCaption,
                      target_width=args.twidth,
                      target_height=args.theight
                      )

    print '\nWrote %d files into: %s'%(len(args.infiles), args.outdir)

if __name__ == '__main__':
    main()
    
