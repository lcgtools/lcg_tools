# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Cloudberries
#
# This file is part of lcgtools
#
# lcgtools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# lcgtools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with lcgtools.  If not, see <https://www.gnu.org/licenses/>.
#

"""Graphics related functionality."""

import os
import pathlib

from lcgtools import LcgException
from PySide6 import QtCore, QtGui

__all__ = ['LcgImage', 'LcgImageTransform', 'LcgAspectRotation',
           'LcgCardPdfGenerator']


class LcgImage(QtGui.QImage):
    """Expands QImage with some additional functionality.

    Overloads all :class:`PySide6.QtGui.QImage` constructors to cast the
    result as an LcgImage.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def addBleed(self, bleed, method='simple'):
        """Adds bleed for the image.

        :param  bleed: amount of bleed to add (in mm)
        :param method: bleed method to apply (for future use)
        :return:       image with added bleed
        :rtype:        :class:`LcgImage`

        The method can only be called if the application has initiated a
        :class:`PySide6.QtWidgets.QApplication`.

        """
        if method != 'simple':
            raise ValueError(f'Method {method} not supported')
        if bleed < 0:
            raise ValueError('Bleed must be non-negative')
        if bleed == 0:
            return self

        # Determine number of pixels to add vertically and horizontally
        w_px, h_px = self.width(), self.height()
        w_mm = w_px*1000/self.dotsPerMeterX()
        h_mm = h_px*1000/self.dotsPerMeterY()
        rel_bleed_w = bleed/(w_mm + 2*bleed)
        rel_bleed_h = bleed/(h_mm + 2*bleed)
        bleed_w_px = int(w_px*rel_bleed_w)
        bleed_h_px = int(h_px*rel_bleed_h)

        new_width = w_px + 2*bleed_w_px
        new_height = h_px + 2*bleed_h_px
        new_img = QtGui.QPixmap(new_width, new_height)
        p = QtGui.QPainter(new_img)
        try:
            p.drawImage(QtCore.QPoint(bleed_w_px, bleed_h_px), self)

            if bleed_w_px > 0:
                # Add missing bleed from left/right side (pad vertically)
                for xpos, offset in ((0, -bleed_w_px),
                                     (w_px - 1, bleed_w_px)):
                    pad_img = self.copy(QtCore.QRect(xpos, 0, 1, h_px))
                    pad_brush = QtGui.QBrush(pad_img)
                    x_origin, y_origin = xpos + bleed_w_px, bleed_h_px
                    p.setBrushOrigin(x_origin, y_origin)
                    p.fillRect(x_origin, bleed_h_px, offset, h_px, pad_brush)

            if bleed_h_px > 0:
                # Add missing bleed from top/bottom side (pad horizontally)
                for ypos, offset in ((0, -bleed_h_px),
                                     (h_px - 1, bleed_h_px)):
                    pad_img = self.copy(QtCore.QRect(0, ypos, w_px, 1))
                    pad_brush = QtGui.QBrush(pad_img)
                    x_origin, y_origin = bleed_w_px, ypos + bleed_h_px
                    p.setBrushOrigin(x_origin, y_origin)
                    p.fillRect(bleed_w_px, y_origin, w_px, offset, pad_brush)

            if min(bleed_w_px, bleed_h_px) > 0:
                # Add missing bleed in corners
                d_w, d_h = bleed_w_px, bleed_h_px
                n_im_w, n_im_h = new_img.width(), new_img.height()
                for params in ((0, 0, 0, 0),
                               (n_im_w-d_w+1, 0, w_px-1, 0),
                               (0, n_im_h-d_h+1, 0, h_px-1),
                               (n_im_w-d_w+1, n_im_h-d_h+1, w_px-1, h_px-1)):
                    xpos, ypos, cpick_x, cpick_y = params
                    fill_color = self.pixel(cpick_x, cpick_y)
                    p.fillRect(xpos, ypos, d_w, d_h, fill_color)
        finally:
            # Painter must be destroyed before its target pixmap
            del p

        # Return adjusted image with appropriate size
        result = LcgImage(new_img.toImage())
        result.setWidthMm(w_mm + 2*bleed)
        result.setHeightMm(h_mm + 2*bleed)
        return result

    def cropBleed(self, bleed):
        """Crops excess bleed for the image.

        :param  bleed: amount of excess bleed to crop (in mm)
        :return:       cropped image
        :rtype:        :class:`LcgImage`

        """
        if bleed < 0:
            raise ValueError('Bleed must be non-negative')
        if bleed == 0:
            return self

        # Determine number of pixels to subtract vertically and horizontally
        w_px, h_px = self.width(), self.height()
        w_mm, h_mm = self.widthMm(), self.heightMm()
        rel_bleed_w = bleed/(w_mm + 2*bleed)
        rel_bleed_h = bleed/(h_mm + 2*bleed)
        bleed_w_px = int(w_px*rel_bleed_w)
        bleed_h_px = int(h_px*rel_bleed_h)

        # Copy appropriate image
        if max(bleed_w_px, bleed_h_px) == 0:
            return self
        new_w_px = w_px - 2*bleed_w_px
        new_h_px = h_px - 2*bleed_h_px
        rect = QtCore.QRect(bleed_w_px, bleed_h_px, new_w_px, new_h_px)
        return LcgImage(self.copy(rect))

    def rotateClockwise(self):
        """Returns the image rotated 90 degrees clockwise."""
        transform = QtGui.QTransform().rotate(90)
        return LcgImage(self.transformed(transform))

    def rotateAntiClockwise(self):
        """Returns the image rotated 90 degrees anticlockwise."""
        transform = QtGui.QTransform().rotate(-90)
        return LcgImage(self.transformed(transform))

    def rotateHalfCircle(self):
        """Returns the image rotated 180 degrees."""
        transform = QtGui.QTransform().rotate(180)
        return LcgImage(self.transformed(transform))

    def widthMm(self):
        """Returns image width in millimeters."""
        return self.width()*1000/self.dotsPerMeterX()

    def setWidthMm(self, width):
        """Sets image width in millimeters.

        :param width: new width in millimeters

        Changes width by manipulating the horizontal dpi resolution; the
        method does not change the number of pixels horizontally.

        """
        self.setDotsPerMeterX(self.width()*1000/width)

    def heightMm(self):
        """Returns image height in millimeters."""
        return self.height()*1000/self.dotsPerMeterY()

    def setHeightMm(self, height):
        """Sets image height in millimeters.

        :param height: new height in millimeters

        Changes height by manipulating the vertical dpi resolution; the
        method does not change the number of pixels vertically.

        """
        self.setDotsPerMeterY(self.height()*1000/height)

    def saveToBytes(self, format='PNG'):
        """Saves the image as a bytes object.

        :param format: image format (as expected by :meth:`QtGui.QImage.save`)
        :param format: str
        :return:       saved image (or None if unable to save)
        :rtype:        bytes

        """
        qba = QtCore.QByteArray()
        qbuf = QtCore.QBuffer(qba)
        qbuf.open(QtCore.QIODevice.WriteOnly)
        if not self.save(qbuf, format):
            return None
        else:
            return qba.data()


class LcgImageTransform(object):
    """Can perform a transform on a :class:`LcgImage`.

    Call the object with a :class:`LcgImage` as an argument, to get
    another :class:`LcgImage` returned as a transformed image. Override
    :meth:`_transform` to change behaviour.

    Input type to :meth:`__call__` is verified to be a :class:`LcgImage`, (or
    is automatically casted from a :class:`QImage`). The return value is
    automatically changed to a :class:`LcgImage` if it is returned by
    :meth:`_transform` as a :class:`QImage`.

    """

    def _transform(self, image):
        """Performs a transform image, returning another image.

        :param image: the image to transform
        :type  image: :class:`QImage` or :class:`LcgImage`
        :return:      transformed image
        :rtype:       :class:`QImage` or :class:`LcgImage`

        Override this method to set the object's transform behaviour.

        """
        raise NotImplementedError()

    def __call__(self, image):
        if not isinstance(image, QtGui.QImage):
            raise TypeError('Image must be QImage or derived class')
        if not isinstance(image, LcgImage):
            image = LcgImage(image)
        result = self._transform(image)
        if not isinstance(result, LcgImage):
            result = LcgImage(result)
        return result


class LcgAspectRotation(LcgImageTransform):
    """Rotates an image if its aspect does not match target.

    :param  portrait: if True convert to portrait aspect, otherwise landscape
    :param clockwise: if True rotate clockwise otherwise anticlockwise
    :param  physical: if True use physical dimension, otherwise pixel count

    """

    def __init__(self, portrait=True, clockwise=False, physical=True):
        self._portrait = portrait
        self._clockwise = clockwise
        self._physical = physical

    def _transform(self, image):
        rotate = False
        portrait = self._portrait
        if self._physical:
            rotate |= portrait and (image.widthMm() > image.heightMm())
            rotate |= (not portrait) and (image.heightMm() > image.widthMm())
        else:
            rotate |= portrait and (image.width() > image.height())
            rotate |= (not portrait) and (image.height() > image.width())
        if rotate:
            if self._clockwise:
                image = image.rotateClockwise()
            else:
                image = image.rotateAntiClockwise()
        return image


class LcgCardPdfGenerator(QtGui.QPdfWriter):
    """Generates PDF document from a set of inputs.

    :param   outfile: filename of output PDF file
    :param  pagesize: page size string ('a4' or 'letter')
    :param       dpi: resolution of generated PDF (dots per inch)
    :param   c_width: card width in mm
    :param  c_height: card height in mm
    :bleed     bleed: card bleed in mm
    :param    margin: page margin in mm, all sides
    :param   spacing: minimum card spacing in mm
    :param      fold: distance from card to fold line
    :param    folded: if True draw foldable pages, if False draw 2-sided
    :param       odd: print even numbered pages for 2-sided print
    :param      even: print even numbered pages for 2-sided print
    :param ex_offset: print xpos offset (in mm) for 2-sided even number pages
    :param ey_offset: print ypos offset (in mm) for 2-sided even number pages

    The offset parameters will shift everything that is printed on even
    numbered pages (the back sides) in 2-sided mode, which enables making
    adjustments for aligning front/back side prints for printers which do not
    align 2-sided printing perfectly.

    """

    def __init__(self, outfile, pagesize, dpi, c_width, c_height, bleed=3,
                 margin=5, spacing=1, fold=3, folded=True):
        self._done = False
        self._painter = None
        self._outfile = None

        if pathlib.Path(outfile).exists():
            raise LcgException(f'Output file {outfile} already exists')
        super().__init__(outfile)

        self._outfile = outfile
        self._pagesize = pagesize
        self._dpi = dpi
        self._c_width = c_width
        self._c_height = c_height
        self._bleed = bleed
        self._margin = margin
        self._spacing = spacing
        self._fold = fold
        self._folded = folded

        self._feed_dir = 'portrait'
        self._odd = True
        self._even = True
        self._ex_offset = 0
        self._ey_offset = 0

        # Create PDF writer for output and set up correct layout
        if pathlib.Path(self._outfile).exists():
            raise LcgException(f'Output file {self._outfile} already exists')
        self.setResolution(self._dpi)
        layout = QtGui.QPageLayout()
        if pagesize.lower() == 'a4':
            _size = QtGui.QPageSize.A4
        elif pagesize.lower() == 'letter':
            _size = QtGui.QPageSize.Letter
        elif pagesize.lower() == 'a3':
            _size = QtGui.QPageSize.A3
        elif pagesize.lower() == 'tabloid':
            _size = QtGui.QPageSize.Tabloid
        else:
            raise LcgException(f'Unknown pagesize {pagesize}')
        layout.setPageSize(_size)
        layout.setOrientation(QtGui.QPageLayout.Landscape)
        _pwm = layout.fullRect(QtGui.QPageLayout.Millimeter).width()
        self._page_width_mm = _pwm
        _phm = layout.fullRect(QtGui.QPageLayout.Millimeter).height()
        self._page_height_mm = _phm
        self.setPageLayout(layout)

        # Calculate card spacing and positions - horizontally
        self._card_current = 0
        c_tot_width = self._c_width + 2*self._bleed
        avail_width = self._page_width_mm
        avail_width -= (2*self._margin + c_tot_width + self._spacing)
        if avail_width < 0:
            raise LcgException('Cannot fit any cards in the width dimension')
        self._cards_per_page = 1 + int(avail_width/(c_tot_width+self._spacing))
        avail_width = self._page_width_mm - 2*self._margin
        space_width = avail_width - self._cards_per_page*c_tot_width
        self._cards_xspace = space_width / (self._cards_per_page + 1)
        self._cards_xstart = self._margin + self._cards_xspace

        # Calculate card positions - vertically
        c_tot_height = self._c_height + 2*self._bleed
        y_center = (self._page_height_mm/2)
        self._cards_front_ypos = y_center - self._fold - c_tot_height
        self._cards_back_ypos = y_center + self._fold

        # Cache of cards (front, back) to be printed for 2-sided printing
        self._card_cache = []

        # Various properties
        self._current_page = 1

    def __del__(self):
        if not self._done:
            self.abort()

    def loadCard(self, image, trans=None, bleed=0, adjust=True):
        """Load card from image and generate scaled QImage with required bleed.

        :param    image: image or file name of image
        :type     image: :class:`QtGui.QImage` or str
        :param    trans: transform to perform on loaded image before other
                         processing (or None)
        :type     trans: :class:`lcgtools.graphics.LcgImageTransform`
        :param    bleed: amount of bleed already existing on image (mm)
        :param   adjust: adjust image to get target bleed set on generator
        :return:         loaded and processed image
        :rtype:          :class:`LcgImage`

        The image is scaled to the correct width and height in pixels to match
        the card size (including bleed) with the dpi resolution set on the
        PDF generator.

        """
        c_tot_width_mm = self._c_width + 2*self._bleed
        c_tot_height_mm = self._c_height + 2*self._bleed
        w_px = self.mm_to_px(c_tot_width_mm)
        h_px = self.mm_to_px(c_tot_height_mm)

        if isinstance(image, QtGui.QImage):
            if isinstance(image, LcgImage):
                img = image
            else:
                img = LcgImage(image)
        else:
            img = LcgImage(image)
            if img.isNull():
                raise LcgException(f'Could not load as QImage: "{image}"')
        if trans:
            if not isinstance(trans, LcgImageTransform):
                raise TypeError('trans argument must be LcgImageTransform')
            img = trans(img)
        img.setWidthMm(self._c_width + 2*bleed)
        img.setHeightMm(self._c_height + 2*bleed)
        if adjust:
            delta_bleed = self._bleed - bleed
            if delta_bleed > 0:
                img = img.addBleed(delta_bleed)
            elif delta_bleed < 0:
                img = img.cropBleed(-delta_bleed)

        # Return image scaled to required dimensions for PDF paint device
        img = img.scaled(QtCore.QSize(w_px, h_px))
        return LcgImage(img)

    def drawCard(self, front=None, back=None, _force=False):
        """Draws a new card onto the PDF.

        :param front: image or color for front side of card
        :type  front: :class:`PySide6.QtGui.PySide6.QtGui.QImage` or
                      :class:`PySide6.QtGui.PySide6.QtGui.QColor`
        :param  back: image or color for back side of card
        :type  front: :class:`PySide6.QtGui.PySide6.QtGui.QImage` or
                      :class:`PySide6.QtGui.PySide6.QtGui.QColor`

        For each card side parameter, if it is a QImage, then that image
        is used for the card side, and it is assumed to include required bleed.
        If the parameter is an a QColor, then a rectangle of that solid color
        is drawn instead. If it is None then a white rectangle is drawn.

        """
        # If printing 2-sided, handle caching and flush when page is full
        if not self._folded and not _force:
            self._card_cache.append((front, back))
            if len(self._card_cache) == 2*self._cards_per_page:
                self._flush_card_cache()
            return

        if self._card_current == 4:
            # Start new PDF page
            self.newPage()
            self._current_page += 1
            self._card_current = 0
        if self._current_page % 2 == 1:
            off_x, off_y = 0, 0
        else:
            off_x = self.mm_to_px(self._ex_offset)
            off_y = self.mm_to_px(self._ey_offset)

        painter = self.painter()

        if self._card_current == 0:
            x_0_px = self.mm_to_px(self._margin)
            x_1_px = self.mm_to_px(self._page_width_mm - self._margin)

            if self._folded:
                # Draw fold line
                pen = QtGui.QPen('Black')
                pen.setWidth(2)
                pen.setStyle(QtCore.Qt.DotLine)
                painter.setPen(pen)
                y_px = self.mm_to_px(self._page_height_mm/2)
                painter.drawLine(x_0_px + off_x, y_px + off_y,
                                 x_1_px + off_x, y_px + off_y)

            # Draw horizontal cut lines
            pen = QtGui.QPen('Black')
            pen.setWidth(2)
            painter.setPen(pen)
            for card_y_mm in self._cards_front_ypos, self._cards_back_ypos:
                card_y_mm += self._bleed
                for y_mm in card_y_mm, card_y_mm + self._c_height:
                    y_px = self.mm_to_px(y_mm)
                    painter.drawLine(x_0_px + off_x, y_px + off_y,
                                     x_1_px + off_x, y_px + off_y)

        # Calculate position and width info for front and back images
        c_tot_width_mm = self._c_width + 2*self._bleed
        c_tot_height_mm = self._c_height + 2*self._bleed
        w_px = self.mm_to_px(c_tot_width_mm)
        h_px = self.mm_to_px(c_tot_height_mm)
        x_mm = self._cards_xstart
        x_mm += self._card_current*(self._cards_xspace + c_tot_width_mm)
        x_px = self.mm_to_px(x_mm)

        # Draw vertical cut lines
        pen = QtGui.QPen('Black')
        pen.setWidth(5)
        painter.setPen(pen)
        y_0_px = self.mm_to_px(self._margin)
        y_1_px = self.mm_to_px(self._page_height_mm - self._margin)
        for x_offset in self._bleed, self._bleed + self._c_width:
            x_px = self.mm_to_px(x_mm + x_offset)
            painter.drawLine(x_px + off_x, y_0_px + off_y,
                             x_px + off_x, y_1_px + off_y)

        # Draw card front and back side
        for card_side, y_mm in ((front, self._cards_front_ypos),
                                (back, self._cards_back_ypos)):
            x_px = self.mm_to_px(x_mm)
            y_px = self.mm_to_px(y_mm)
            if card_side is None:
                card_side = QtGui.QColor('White')
            if isinstance(card_side, QtGui.QImage):
                img = card_side
                img_pos = QtCore.QPoint(x_px + off_x, y_px + off_y)
                painter.drawImage(img_pos, img)
            elif isinstance(card_side, QtGui.QColor):
                pen = QtGui.QPen('Black')
                pen.setWidth(5)
                painter.setPen(pen)
                old_brush = painter.brush()
                brush = QtGui.QBrush()
                brush.setColor(card_side)
                brush.setStyle(QtCore.Qt.SolidPattern)
                painter.setBrush(brush)
                pen = QtGui.QPen('Black')
                painter.drawRect(x_px + off_x, y_px + off_y, w_px, h_px)
                painter.setBrush(old_brush)
            else:
                raise TypeError('Must be QImage or QColor')

        self._card_current += 1

    def abort(self, remove=True):
        """Aborts writing to PDF document.

        :param remove: if True remove the PDF file that was created.

        """
        if self._done:
            raise LcgException('Cannot close or abort more than once')
        if self._painter:
            self._painter.end()
            self._painter = None
        self._done = True
        if (remove and self._outfile is not None
            and os.path.exists(self._outfile)):
            os.remove(self._outfile)

    def finish(self):
        """Finishes the PDF document, ending the painter."""
        if self._done:
            raise LcgException('Cannot close or abort more than once')
        if not self._folded:
            self._flush_card_cache()
        if self._painter:
            self._painter.end()
            self._painter = None
        self._done = True

    def mm_to_px(self, offset_mm):
        """Converts offset in mm to offset in pixels (using pdf dpi)."""
        return int(offset_mm*self._dpi/25.4)

    def px_to_mm(self, offset_px):
        """Converts offset in pixels to offset in mm (using pdf dpi)"""
        return offset_px*25.4/self._dpi

    def painter(self):
        """Returns the painter of this PDF generator (if active)."""
        if self._done:
            raise LcgException('Writing was closed or aborted')
        if self._painter is None:
            self._painter = QtGui.QPainter(self)
            self._painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        return self._painter

    def setTwosidedSubset(self, odd, even):
        """Specify which pages to include for 2-sided printing.

        :param  odd: if True include odd numbered (card front) pages
        :param even: if True include even numbered (card back) pages

        Method must be called before a painter is initiated on PDF generator.

        """
        if self._painter or self._done:
            raise LcgException('Cannot set offset after painting initiated')
        self._odd = odd
        self._even = even

    def setTwosidedEvenPageOffset(self, offset_x, offset_y):
        """Set offset for even numbered pages with 2-sided printing.

        :param offset_x: horizontal offset in mm
        :param offset_y: vertical offset in mm

        Method must be called before a painter is initiated on PDF generator.

        """
        if self._painter or self._done:
            raise LcgException('Cannot set offset after painting initiated')
        self._ex_offset = offset_x
        self._ey_offset = offset_y

    def setFeedDir(self, feed_dir):
        """Specify feed direction for 2-sided printing.

        :param feed_dir: feed aspect, either "portrait" or "landscape"
        :type  feed_dir: str

        Method must be called before a painter is initiated on PDF generator.

        """
        if self._painter or self._done:
            raise LcgException('Cannot set offset after painting initiated')
        feed_dir = feed_dir.lower()
        if feed_dir not in ('portrait', 'landscape'):
            raise LcgException(f'Illegal aspect value: {feed_dir}')
        self._feed_dir = feed_dir

    @property
    def cards_per_page(self):
        """Max number of cards fitted per page of PDF document."""
        return self._cards_per_page

    def _flush_card_cache(self):
        """Draws the cards in the card cache (for 2-sided printing)."""
        if not self._card_cache:
            return
        cards_per_row = self._cards_per_page
        cards_per_page = 2*cards_per_row
        fronts, backs = zip(*(self._card_cache))
        fronts, backs = list(fronts), list(backs)
        fronts += [None]*(cards_per_page - len(self._card_cache))
        backs += [None]*(cards_per_page - len(self._card_cache))

        fronts_top = fronts[:cards_per_row]
        fronts_bottom = fronts[cards_per_row:]

        if self._feed_dir == 'landscape':
            backs_top = backs[:cards_per_row]
            backs_top.reverse()
            backs_bottom = backs[cards_per_row:]
            backs_bottom.reverse()
        elif self._feed_dir == 'portrait':
            backs_top = backs[cards_per_row:]
            backs_bottom = backs[:cards_per_row]
            for img_list in backs_top, backs_bottom:
                for i, img in enumerate(img_list):
                    if img:
                        img_list[i] = img.rotateHalfCircle()
        else:
            raise NotImplementedError('Should never happen')

        print_set = []
        if self._odd:
            # Draw card fronts
            print_set.append((fronts_top, fronts_bottom))
        if self._even:
            print_set.append((backs_top, backs_bottom))

        for tops, bottoms in print_set:
            for top, bottom in zip(tops, bottoms):
                self.drawCard(top, bottom, _force=True)

        self._card_cache = []
