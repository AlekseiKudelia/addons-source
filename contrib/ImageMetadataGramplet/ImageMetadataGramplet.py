#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2009-2011 Rob G. Healey <robhealey1@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# $Id$

#------------------------------------------------
#   Internaturlization
#------------------------------------------------
from TransUtils import get_addon_translator
_ = get_addon_translator().ugettext

# ***********************************************
# Python Modules
# ***********************************************
import os, sys
from datetime import datetime, date
import time, calendar

#------------------------------------------------
# GTK modules
#------------------------------------------------
import gtk

# -----------------------------------------------
# GRAMPS modules
# -----------------------------------------------
from QuestionDialog import OkDialog, WarningDialog

from gen.plug import Gramplet
from DateHandler import displayer as _dd

import gen.mime
import gen.lib
import Utils
from PlaceUtils import conv_lat_lon

#####################################################################
#               pyexiv2 check for library...?
#####################################################################

# pyexiv2 download page (C) Olivier Tilloy
_DOWNLOAD_LINK = "http://tilloy.net/dev/pyexiv2/download.html"

# make sure the pyexiv2 library is installed and at least a minimum version
software_version = False
Min_VERSION = (0, 1, 3)
Min_VERSION_str = "pyexiv2-%d.%d.%d" % Min_VERSION
Pref_VERSION_str = "pyexiv2-%d.%d.%d" % (0, 3, 0)

# for users of pyexiv2 prior to 0.2.0...
LesserVersion = False

try:
    import pyexiv2
    software_version = pyexiv2.version_info

except ImportError, msg:
    WarningDialog( str(msg) )
    raise Exception(_("Failed to load 'Image Metadata Gramplet/ Addon'..."))
               
# This only happens if the user has prior than pyexiv2-0.2.0 installed on their computer...
# it requires the use of a few different things, which you will see when this variable is called...
except AttributeError:
    LesserVersion = True

# the library is either not installed or does not meet 
# minimum required version for this addon....
if (software_version and (software_version < Min_VERSION)):
    msg = _("The minimum required version for pyexiv2 must be %s \n"
        "or greater.  Or you do not have the python library installed yet.  "
        "You may download it from here: %s\n\n  I recommend getting, %s") % (
         Min_VERSION_str, _DOWNLOAD_LINK, Pref_VERSION_str)
    raise Exception(msg)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
# set up Exif keys for key sections of:
# Opening, Description, Origin, Image, Camera, Addvanced KeyTags
_OPENING = dict( [v, k] for v, k in {
    "Exif.Image.ImageDescription" : "ImageDescription",
    "Exif.Image.Artist"  : "ImageArtist",
    "Exif.Image.Copyright" : "ImageCopyright",
    "Exif.Image.DateTime" : "ImageDateTime",
    "Exif.GPSInfo.GPSAltitudeRef" : "ImageAltitudeRef",
    "Exif.GPSInfo.GPSAltitude" : "ImageAltitude",
    "Exif.GPSInfo.GPSTimeStamp" : "GPSTimeStamp",
    "Exif.GPSInfo.GPSSatellites" : "GPSSatellites", 
    "Exif.GPSInfo.GPSLatitudeRef" : "ImageLatitudeRef",
    "Exif.GPSInfo.GPSLatitude" : "ImageLatitude",
    "Exif.GPSInfo.GPSLongitudeRef" : "ImageLongitudeRef",
    "Exif.GPSInfo.GPSLongitude" : "ImageLongitude"}.items() )

_DESCRIPTION = dict( [v, k] for v, k in {
    "Exif.Image.ImageDescription" : "ImageDescription",
    "Exif.Image.XPSubject" : "XPSubject",
    "Exif.Image.Rating" : "ImageRating",
    "Exif.Image.XPKeywords" : "XPKeywords",
    "Exif.Image.XPComment" : "XPComment"}.items() )

_ORIGIN = dict( [v, k] for v, k in {
    "Exif.Image.Artist"  : "ImageArtist",
    "Exif.Image.Copyright" : "ImageCopyright",
    "Exif.Photo.DateTimeOriginal" : "ImageDateTime",
    "Exif.Image.Software" : "Software"}.items() )

_IMAGE = dict( [v, k] for v, k in {
    "Exif.Photo.PixelXDimension" : "Width",
    "Exif.Photo.PixelYDimension" : "Height",
    "Exif.Image.XResolution" : "HorizontalResolution",
    "Exif.Image.YResolution" : "VerticalResolution",
    "Exif.Image.ResolutionUnit" : "ResolutionUnit",
    "Exif.Photo.ColorSpace" : "ColourRepresentation",
    "Exif.Photo.CompressedBitsPerPixel" : "CompressedBits"}.items() )
      
_CAMERA = dict( [v, k] for v, k in {
    "Exif.Image.Make"  : "CameraMaker",
    "Exif.Image.Model" : "CameraModel",
    "Exif.Photo.FNumber" : "FStop",
    "Exif.Photo.ExposureTime" : "ExposureTime",
    "Exif.Photo.ISOSpeedRatings" : "SpeedRatings",
    "Exif.Photo.ExposureBiasValue" : "ExposureBias",
    "Exif.Photo.FocalLength" : "FocalLength",
    "Exif.Photo.MaxAperatureValue" : "AperatureValue",
    "Exif.Photo.Flash" : "Flash",
    "Exif.Photo.FocalLengthIn35mmFilm" : "Focal35mmFilm"}.items() )

_ADVANCED = dict( [v, k] for v, k in {
    "Xmp.MicrosoftPhoto.LensManufacturer" : "LensMaker",
    "Xmp.MicrosoftPhoto.LensModel" : "LensModel",
    "Xmp.MicrosoftPhoto.FlashManufacturer" : "FlashMaker",
    "Xmp.MicrosoftPhoto.FlashModel" : "FlashModel",
    "Xmp.MicrosoftPhoto.CameraSerialNumber" : "CameraSerialNumber",
    "Exif.Photo.Contrast" : "Contrast",
    "Exif.Photo.LightSource" : "LightSource",
    "Exif.Photo.ExposureProgram" : "ExposureProgram",
    "Exif.Photo.Saturation" : "Saturation",
    "Exif.Photo.Sharpness" : "Sharpness",
    "Exif.Photo.WhiteBalance" : "WhiteBalance",
    "Exif.Image.ExifTag" : "ExifVersion"}.items() )

_GPS = dict( [v, k] for v, k in {
    "Exif.GPSInfo.GPSAltitudeRef" : "ImageAltitudeRef",
    "Exif.GPSInfo.GPSAltitude" : "ImageAltitude",
    "Exif.GPSInfo.GPSTimeStamp" : "GPSTimeStamp",
    "Exif.GPSInfo.GPSSatellites" : "GPSSatellites", 
    "Exif.GPSInfo.GPSLatitudeRef" : "ImageLatitudeRef",
    "Exif.GPSInfo.GPSLatitude" : "ImageLatitude",
    "Exif.GPSInfo.GPSLongitudeRef" : "ImageLongitudeRef",
    "Exif.GPSInfo.GPSLongitude" : "ImageLongitude"}.items() )

def _help_clicked():
    """
    Display the relevant portion of GRAMPS manual
    """
    import GrampsDisplay

    GrampsDisplay.help(webpage = 'Image Metadata Gramplet')

def _set_value(pluginobject, KeyTag, KeyValue):
    """
    sets the value for the Exif keys

    @param: pluginobject -- plugin media instance
    @param: KeyTag   -- exif key
    @param: KeyValue -- value to be saved
    """

    # LesserVersion would only be True when pyexiv2-to 0.1.3 is installed
    if LesserVersion:
        pluginobject[KeyTag] = KeyValue 
    else:
        # Exif KeyValue family?
        if "Exif" in KeyTag:
            try:
                pluginobject[KeyTag].value = KeyValue

            except KeyError:
                pluginobject[KeyTag] = pyexiv2.ExifTag(KeyTag, KeyValue)

            except (ValueError, AttributeError):
                pass

        # Iptc KeyValue family?
        elif "Iptc" in KeyTag:
            try:
                pluginobject[KeyTag].values = KeyValue

            except KeyError:
                pluginobject[KeyTag] = pyexiv2.IptcTag(KeyTag, KeyValue)

            except (ValueError, AttributeError):
                pass

        # Xmp KeyValue family?
        elif "Xmp" in KeyTag:
            try:
                pluginobject[KeyTag].values = KeyValue

            except KeyError:
                pluginobject[KeyTag] = pyexiv2.XmpTag(KeyTag, KeyValue)

            except (ValueError, AttributeError):
                pass

def _return_month(month):
    """
    returns either an integer of the month number or the abbreviated month name

    @param: rmonth -- can be one of:
        10, "10", "Oct", "October"
    """

    _allmonths = list([_dd.short_months[i], _dd.long_months[i], i] for i in range(1, 13) )

    for sm, lm, index in _allmonths:
        if isinstance(month, str):
            found = any(month == value for value in [sm, lm])
            if found:
                month = int(index)
                break

        else:
            if str(month) == index:
                month = lm
                break
    return month

def _split_values(text):
    """
    splits a variable into its pieces
    """

    if "-" in text:
        separator = "-"
    elif "." in text:
        separator = "."
    elif ":" in text:
        separator = ":"
    else:
        separator = " "

    return [value for value in text.split(separator)]

# ------------------------------------------------------------------------
# Gramplet class
# ------------------------------------------------------------------------
class imageMetadataGramplet(Gramplet):

    def init(self):

        self.exif_widgets = {}

        self.orig_image   = False
        self.plugin_image = False
        self.__full_path  = False

        root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(root)
        root.show_all()

        # connect the database signals...
        self.dbstate.db.connect('media-update', self.update)
        self.dbstate.db.connect("media-rebuild", self.update)

    def active_changed(self, handle):
        """
        Called when the active media is changed.
        """
        self.update()

    def __create_gui(self):
        """
        Create and display the GUI components of the gramplet.
        """
        vbox = gtk.VBox()

        medialabel = gtk.HBox(False)
        self.exif_widgets["Media:Label"] = gtk.Label(_("Click a media object to begin...") )
        self.exif_widgets["Media:Label"].set_alignment(0.0, 0.5)
        medialabel.pack_start(self.exif_widgets["Media:Label"], expand =False)

        mimetype = gtk.HBox(False)
        self.exif_widgets["Mime:Type"] = gtk.Label()
        self.exif_widgets["Mime:Type"].set_alignment(0.0, 0.5)
        mimetype.pack_start(self.exif_widgets["Mime:Type"], expand =False)

        messagearea = gtk.HBox(False)
        self.exif_widgets["Message:Area"] = gtk.Label()
        self.exif_widgets["Message:Area"].set_alignment(0.0, 0.5)
        messagearea.pack_start(self.exif_widgets["Message:Area"], expand =False)

        self.model = gtk.ListStore(object, str, str)
        view = gtk.TreeView(self.model)

        # Key Column
        view.append_column( self.__create_column(_("Key"), 1) )

        # Value Column
        view.append_column( self.__create_column(_("Value"), 2) )

        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_START)

        # description metadata button in button box...
        button_box.add( self.__create_button(
            "Description", _("Description"), self.__description_metadata) )

        # origin metadata button in button box...
        button_box.add( self.__create_button(
            "Origin", _("Origin"), self.__origin_metadata) )

        # image metadata button in button box...
        button_box.add( self.__create_button(
            "Image", _("Image"), self.__image_metadata) )
        vbox.pack_start(button_box, expand =False, fill =False)

        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_START)

        # camera metadata button in button box...
        button_box.add( self.__create_button(
            "Camera", _("Camera"), self.__camera_metadata) )

        # advanced metadata  button in button box...
        button_box.add( self.__create_button(
            "Advanced", _("Advanced"), self.__advanced_metadata) )

        # advanced metadata  button in button box...
        button_box.add( self.__create_button(
            "GPS", _("GPS"), self.__gps_metadata) )
        vbox.pack_start(button_box, expand =False, fill =False)

        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_START)

        # Help button on plugin bar
        button_box.add( self.__create_button(
            "Help", False, _help_clicked, gtk.STOCK_HELP) )

        # Save button on plugin bar
        save = gtk.Button(stock=gtk.STOCK_SAVE)
        save.connect("clicked", self.__save_metadata, view.get_selection() )
        self.exif_widgets["Save"] = save
        button_box.add( self.exif_widgets["Save"] )
                
        # Edit button on plugin bar
        edit = gtk.Button(stock=gtk.STOCK_EDIT)
        edit.connect("clicked", self.__edit_metadata, view.get_selection() )
        self.exif_widgets["Edit"] = edit
        button_box.add( self.exif_widgets["Edit"] )

        # Clear Button on plugin bar
        button_box.add( self.__create_button(
            "Clear", False, self.__clear_metadata, gtk.STOCK_CLEAR) )

        vbox.pack_start(medialabel, expand =False, padding =10)
        vbox.pack_start(mimetype, expand =False, padding =10)
        vbox.pack_start(messagearea, expand =False, padding =10)
        vbox.pack_start(view, padding =10)
        vbox.pack_end(button_box, expand =False, fill =False)

        return vbox

    def __create_column(self, name, colnum, fixed =True):
        """
        will create the column for the column row...
        """

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(name, renderer, text =colnum)

        if fixed:
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            column.set_expand(True)

        else:
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            column.set_expand(False)

        column.set_alignment(0.0)
        column.set_sort_column_id(colnum)

        return column

    def __create_button(self, pos, text, callback, icon =False):
        """
        Creates a button with either text or a stock icon from gtk
        """

        # is there a stock icon for this button?
        if icon:
            button = gtk.Button(stock=icon)

        else:
            button = gtk.Button(text)
            button.set_sensitive(False)

        button.connect("clicked", callback)

        self.exif_widgets[pos] = button

        return button

    def __description_metadata(self, obj):
        """
        displays the description set of tags...
        """

        # read the image metadata for the _DESCRIPTION section and displays it
        self.display_exif_tags(self.__full_path, _DESCRIPTION)

    def __origin_metadata(self, obj):
        """
        displays the origin set of tags...
        """

        # read the image metadata for the _ORIGIN section and displays it
        self.display_exif_tags(self.__full_path, _ORIGIN)

    def __image_metadata(self, obj):
        """
        displays the image set of tags...
        """

        # read the image metadata for the _IMAGE section and displays it
        self.display_exif_tags(self.__full_path, _IMAGE)

    def __camera_metadata(self, obj):
        """
        displays the camera set of tags...
        """

        # read the image metadata for the _CAMERA section and displays it
        self.display_exif_tags(self.__full_path, _CAMERA)

    def __advanced_metadata(self, obj):
        """
        displays the advanced set of tags...
        """

        # read the image metadata for the _ADVANCED section and displays it
        self.display_exif_tags(self.__full_path, _ADVANCED)

    def __gps_metadata(self, obj):
        """
        displays the advanced set of tags...
        """

        # read the image metadata for the _ADVANCED section and displays it
        self.display_exif_tags(self.__full_path, _GPS)

    def __save_metadata(self, widget, selection):
        """
        Saves the image metadata.
        """
        model, iter_ = selection.get_selected()
        if iter_ and not self._dirty_write:
            media = model.get_value(iter_, 0)

            try:
                MetadataSave(self.gui.dbstate, self.gui.uistate, [], media)

            except Errors.WindowActiveError:
                pass

    def __edit_metadata(self, widget, selection):
        """
        Edit the selected media.
        """
        model, iter_ = selection.get_selected()
        if iter_:
            media = model.get_value(iter_, 0)

            try:
                MetadataEditor(self.gui.dbstate, self.gui.uistate, [], media, self.exif_widgets)

            except Errors.WindowActiveError:
                pass

    def __clear_metadata(self, obj):
        """
        clears all data fields to nothing
        """
        self.model.clear()

    def main(self): # return false finishes
        """
        get the active media, mime type, and reads the image metadata
        """
        db = self.dbstate.db

        active_handle = self.get_active("Media")
        if not active_handle:
            return

        # clear Media:Label, Mime:Type, and Message:Area...
        self.exif_widgets["Media:Label"].set_text("")
        self.exif_widgets["Mime:Type"].set_text("")
        self.exif_widgets["Message:Area"].set_text("")

        self.orig_image = db.get_object_from_handle(active_handle)
        if not self.orig_image:
            self.exif_widgets["Message:Area"].set_text(_("No active media selected..."))
            return

        # clear the display area
        self.model.clear()

        # get media full path
        self.__full_path = Utils.media_path_full(self.dbstate.db, self.orig_image.get_path() )

        # check media read/ write priviledges...
        self.__readable = os.access(self.__full_path, os.R_OK)
        self.__writable = os.access(self.__full_path, os.W_OK)
        permissions, filemsg = True, False
        if (not self.__readable and not self.__writable):
            permissions = False
            filemsg = _("You do NOT have read/ write access to this media object.  "
                "Please check your file permissions...")

        elif not self.__readable:
            permissions = False
            filemsg = _("You do NOT have read access to this media object.  "
                "Please check your file permissions...")

        elif not self.__writable:
            permissions = False
            filemsg = _("You do NOT have write access to this media object.  "
                "Please check your file permissions...")

        # if there is a file priviledges/ permissions problem, display it...
        if (not permissions and filemsg):
            self.exif_widgets["Save"].set_sensitive(False)
            self.exif_widgets["Edit"].set_sensitive(False)

            self.exif_widgets["Message:Area"].set_text(filemsg)
            if not self.__readable:
                return

        # display file description/ title...
        self.exif_widgets["Media:Label"].set_text( self.orig_image.get_description() )

        # get media mime type
        mime_type = self.orig_image.get_mime_type()
        self.__mtype = gen.mime.get_description(mime_type)
        self.exif_widgets["Mime:Type"].set_text(self.__mtype)
        if (mime_type and mime_type.startswith("image") ):

                # set up tooltips text for all buttons
                self.__setup_tooltips(self.orig_image)

                # read the media metadata and display it
                self.display_exif_tags(self.__full_path, _OPENING)

        else:
            self.__mtype = False
            self.exif_widgets["Message:Area"].set_text(_("Please choose a different media object..."))

        # disable save and edit buttons if errors or non mime_type media?
        if (not permissions or not self.__mtype):
            self.exif_widgets["Save"].set_sensitive(False)
            self.exif_widgets["Edit"].set_sensitive(False)

            return

    def __get_value(self, KeyTag):
        """
        gets the value from the Exif Key, and returns it...

        @param: KeyTag -- image metadata key
        """

        KeyValue = ""

        # LesserVersion would only be True when pyexiv2-to 0.1.3 is installed
        if LesserVersion:
            KeyValue = self.plugin_image[KeyTag]

        else:
            try:
                KeyValue = self.plugin_image[KeyTag].value

            except (KeyError, ValueError, AttributeError):
                pass

        return KeyValue

    def __button_sensitivity(self, obj):
        """
        will determine if a button should be available or not?

        if there are no key values for this section, disable/ grey out the button?
        """

        # prevent non mime type media objects from seeing the buttons
        if not self.__mtype:
            return

        # if there is no values in Description section?
        if [keytag for keytag in _DESCRIPTION.keys() if self.__get_value(keytag) ]:
            self.exif_widgets["Description"].set_sensitive(True)

        # if there is no values in Origin section?
        if [keytag for keytag in _ORIGIN.keys() if self.__get_value(keytag) ]:
            self.exif_widgets["Origin"].set_sensitive(True)

        # if there is no values in Image section?
        if [keytag for keytag in _IMAGE.keys() if self.__get_value(keytag) ]:
            self.exif_widgets["Image"].set_sensitive(True)

        # if there is no values in Camera section?
        if [keytag for keytag in _CAMERA.keys() if self.__get_value(keytag) ]:
            self.exif_widgets["Camera"].set_sensitive(True)

        # if there is no values in Advanced section?
        if [keytag for keytag in _ADVANCED.keys() if self.__get_value(keytag) ]:
            self.exif_widgets["Advanced"].set_sensitive(True)

        # if there is no values in GPS section?
        if [keytag for keytag in _GPS.keys() if self.__get_value(keytag) ]:
            self.exif_widgets["GPS"].set_sensitive(True)

    def __setup_tooltips(self, obj):
        """
        setup tooltips for each field
        """

        # sets tooltip text for the Description button
        self.exif_widgets["Description"].set_tooltip_text(_("Displays the key tag/ "
            "value pairs for the Description tags."))

        # sets tooltip text for the Origin button
        self.exif_widgets["Origin"].set_tooltip_text(_("Displays the key tag/ "
            "value pairs for the Origin tags."))

        # sets tooltip text for the Image button
        self.exif_widgets["Image"].set_tooltip_text(_("Displays the key tag/ "
            "value pairs for the Image tags."))

        # sets tooltip text for the Camera button
        self.exif_widgets["Camera"].set_tooltip_text(_("Displays the key tag/ "
            "value pairs for the Camera tags."))

        # sets tooltip text for the Advanced button
        self.exif_widgets["Advanced"].set_tooltip_text(_("Displays the key tag/ "
            "value pairs for the Advanced tags."))

        # sets tooltip text for the GPS button
        self.exif_widgets["GPS"].set_tooltip_text(_("Displays the key tag/ "
            "value pairs for the GPS tags."))

        # sets tooltip text for the Help button
        self.exif_widgets["Help"].set_tooltip_text(_("Diplays the Wiki Help Page for "
            "this Gramps addon/ gramplet."))

        # sets tooltip text for the Save button
        self.exif_widgets["Save"].set_tooltip_text(_("Saves the media "
            "metadata for this media object."))

        # sets tooltip text for the Edit button
        self.exif_widgets["Edit"].set_tooltip_text(_("Edits the active "
            "media's metadata."))

        # sets tooltip text for the Clear button
        self.exif_widgets["Clear"].set_tooltip_text(_("Clears all the image "
            "metadata key values."))

    def display_exif_tags(self, full_path, metadataTags):
        """
        reads the image metadata after the pyexiv2.Image has been created

        @param: full_path -- complete path to media object on local computer
        @param: metadataTags -- a list of the exif keytags that we will be displayed...
        """
        MediaDataTags = []
        self.model.clear()

        if LesserVersion:  # prior to pyexiv2-0.2.0
            self.plugin_image = pyexiv2.Image(full_path)

            self.plugin_image.readMetadata()

            # get all keytags for this section of tags and if there is a value?
            MediaDataTags = [keytag for keytag in self.plugin_image.exifKeys()
                    if keytag in metadataTags ]

            # get all keytags for this section of tags and if there is a value?
            MediaDataTags.append( [keytag for keytag in self.plugin_image.xmpKeys()
                    if keytag in metadataTags ] )

            # get all keytags for this section of tags and if there is a value?
            MediaDataTags.append( [keytag for keytag in self.plugin_image.iptcKeys()
                    if keytag in metadataTags ] )

        else: # pyexiv2-0.2.0 and above
            self.plugin_image = pyexiv2.ImageMetadata(full_path)

            self.plugin_image.read()

            # get all keytags for this section of tags and if there is a value?
            MediaDataTags = [keytag for keytag in self.plugin_image.exif_keys
                    if keytag in metadataTags ]

            # get all keytags for this section of tags and if there is a value?
            MediaDataTags.append( [keytag for keytag in self.plugin_image.xmp_keys
                    if keytag in metadataTags ] )

            # get all keytags for this section of tags and if there is a value?
            MediaDataTags.append( [keytag for keytag in self.plugin_image.iptc_keys
                    if keytag in metadataTags ] )

        # check to see if a section/ button should be inactive/ greyed out for lack of data?
        self.__button_sensitivity(self.plugin_image)

        # check to see if we got metadata from media object?
        for KeyTag in MediaDataTags:

            tagValue = self.__get_value(KeyTag)
            if tagValue:

                if LesserVersion: # prior to pyexiv2-0.2.0
                    label = self.plugin_image.tagDetails(KeyTag)[0]
                    human_value = self.plugin_image.interpretedExifValue(KeyTag)

                else:  # pyexiv2-0.2.0 and above
                    tag = self.plugin_image[KeyTag]
                    label = tag.label
                    human_value = tag.human_value

                # if keytag is Latitude/ Longitude, display deg, min, sec?
                if KeyTag in ["Exif.GPSInfo.GPSLatitude", "Exif.GPSInfo.GPSLongitude"]:
                    deg, min, sec = rational_to_dms(tagValue)
                    tagValue = """%s° %s′ %s″""" % (deg, min, sec)

                # if KeyTag is LatitudeRef/ LongitudeRef, display human value instead? 
                if KeyTag in ["Exif.GPSInfo.GPSLatitudeRef", "Exif.GPSInfo.GPSLongitudeRef"]:
                    tagValue = human_value
            
                # add tagValue to display...
                self.model.append( (self.plugin_image, label, tagValue) )

    def post_init(self):
        self.connect_signal("Media", self.update)

def __convert_value(value):
    """
    will take a value from the coordinates and return its value
    """
    from fractions import Fraction
    from decimal import *
    getcontext().prec = 5

    if (isinstance(value, Fraction) or isinstance(value, pyexiv2.Rational) ):
        return str( (Decimal(value.numerator) / Decimal(value.denominator)) )

    return value

def rational_to_dms(coords):
    """
    takes a rational set of coordinates and returns (degrees, minutes, seconds)
    """

    deg, min, sec = False, False, False
    if len(coords) == 3:
        deg, min, sec = coords[0], coords[1], coords[2]

        return [ __convert_value(coordinate) for coordinate in [deg, min, sec] ]
    return deg, min, sec

#################################################
#    Metadata Editor Class
#################################################
import ManagedWindow
from gui.widgets import MonitoredEntry
import GrampsDisplay

class MetadataEditor(ManagedWindow.ManagedWindow):
    """
    Media Metadata Editor.
    """

    def __init__(self, dbstate, uistate, track, media, widgets):

        self.dbstate = dbstate
        self.uistate = uistate
        self.track = track
        self.db = dbstate.db
        self.media = media
        self.exif_widgets = widgets

        ManagedWindow.ManagedWindow.__init__(self, uistate, track, media)

        self.widgets = {}
        top = self.__create_gui()
        self.set_window(top, None, self.get_menu_title() )

    def get_menu_title(self):
        """
        Get the menu title.
        """
        if self.media.get_handle():
            title = self.media.get_description()
            if not title:
                title = _("Unknoen") 
            dialog_title = _('Media: %s') % title
        else:
            dialog_title = _('New Media')
        return dialog_title

#################################################
#          Metadata Save
#################################################
import ManagedWindow
from gui.widgets import MonitoredEntry

class MetadataSave(ManagedWindow.ManagedWindow):
    """
    Media Metadata Saver
    """

    def __init__(self, dbstate, uistate, track, media):

        self.dbstate = dbstate
        self.uistate = uistate
        self.track = track
        self.db = dbstate.db
        
        self.media = media

        ManagedWindow.ManagedWindow.__init__(self, uistate, track, media)

        self.widgets = {}
        top = self.__create_gui()
        self.set_window(top, None, _("Metadata Save") )

#------------------------------------------------
#     Writes/ saves metadata to image
#------------------------------------------------
    def save_metadata(self, obj):
        """
        gets the information from the plugin data fields
        and sets the keytag = keyvalue image metadata
        """

        # check write permissions for this image
        if not self._dirty_write:

            # Author data field
            artist = self.exif_widgets["Author"].get_text()
            if (self.artist is not artist):
                self._set_value(ImageArtist, artist)

            # Copyright data field
            copyright = self.exif_widgets["Copyright"].get_text()
            if (self.copyright is not copyright):
                self._set_value(ImageCopyright, copyright)

            # get date from data field for saving
            wdate = self._write_date( self.exif_widgets["NewDate"].get_text(),
                                 self.exif_widgets["NewTime"].get_text() )
            if wdate is not False: 
                self._set_value(ImageDateTime, wdate)

            # get Latitude/ Longitude from this addon...
            latitude  =  self.exif_widgets["Latitude"].get_text()
            longitude = self.exif_widgets["Longitude"].get_text()

            # check to see if Latitude/ Longitude exists?
            if (latitude and longitude):

                # complete some error checking to prevent crashes...
                # if "?" character exist, remove it?
                if ("?" in latitude or "?" in longitude):
                    latitude = latitude.replace("?", "")
                    longitude = longitude.replace("?", "")

                # if "," character exists, remove it?
                if ("," in latitude or "," in longitude): 
                    latitude = latitude.replace(",", "")
                    longitude = longitude.replace(",", "") 

                # if it is in decimal format, convert it to DMS?
                # if not, then do nothing?
                self.convert2dms(self.plugin_image)

                # get Latitude/ Longitude from the data fields
                latitude  =  self.exif_widgets["Latitude"].get_text()
                longitude = self.exif_widgets["Longitude"].get_text()

                # will add (degrees, minutes, seconds) symbols if needed?
                # if not, do nothing...
                latitude, longitude = self.addsymbols2gps(latitude, longitude)

                # set up display
                self.exif_widgets["Latitude"].set_text(latitude)
                self.exif_widgets["Longitude"].set_text(longitude)

                LatitudeRef = " N"
                if "S" in latitude:
                    LatitudeRef = " S"
                latitude = latitude.replace(LatitudeRef, "")
                LatitudeRef = LatitudeRef.replace(" ", "")

                LongitudeRef = " E"
                if "W" in longitude:
                    LongitudeRef = " W"
                longitude = longitude.replace(LongitudeRef, "")
                LongitudeRef = LongitudeRef.replace(" ", "")

                # remove symbols for saving Latitude/ Longitude GPS Coordinates
                latitude, longitude = _removesymbols4saving(latitude, longitude) 

                # convert (degrees, minutes, seconds) to Rational for saving
                self._set_value(ImageLatitude, coords_to_rational(latitude))
                self._set_value(ImageLatitudeRef, LatitudeRef)

                # convert (degrees, minutes, seconds) to Rational for saving
                self._set_value(ImageLongitude, coords_to_rational(longitude))
                self._set_value(ImageLongitudeRef, LongitudeRef)

            # description data field
            start = self.exif_widgets["Description"].get_start_iter()
            end = self.exif_widgets["Description"].get_end_iter()
            meta_descr = self.exif_widgets["Description"].get_text(start, end)
            if (self.description is not meta_descr):
                self._set_value(ImageDescription, meta_descr)

            # writes the metdata KeyTags to the image...  
            # LesserVersion would only be True when pyexiv2-to 0.1.3 is installed
            if not LesserVersion:
                self.plugin_image.write()
            else:
                self.plugin_image.writeMetadata()

            # notify the user of successful write...
            OkDialog(_("Image metadata has been saved."))

        else:
            ErrorDialog(_("There is an error with this image!\n"
                "You may not have write access or privileges for this image?"))

#------------------------------------------------
# Process Date/ Time fields for saving to image
#------------------------------------------------
    def _write_date(self, wdate = False, wtime = False):
        """
        process the date/ time for writing to image

        @param: wdate -- date from the interface
        @param: wtime -- time from the interface
        """

        # set to initial values, so if it is something wrong,
        # so we can catch it...?
        wyear, wmonth, wday = False, False, False
        hour, minutes, seconds = False, False, False

        # if date is in proper format: 1826-Apr-12 or 1826-April-12
        if (wdate and wdate.count("-") == 2):
            wyear, wmonth, wday = _split_values(wdate)

        # if time is in proper format: 14:06:00
        if (wtime and wtime.count(":") == 2):
            hour, minutes, seconds = _split_values(wtime)

        # if any value for date or time is False, then do not save date
        bad_datetime = any(value == False for value in [wyear, wmonth, wday, hour, minutes, seconds] )
        if not bad_datetime:

            # convert each value for date/ time
            try:
                wyear, wday = int(wyear), int(wday)
            except ValueError:
                pass

            try:
                hour, minutes, seconds = int(hour), int(minutes), int(seconds)
            except ValueError:
                pass

            if wdate is not False:

                # do some error trapping...
                if wday == 0:
                    wday = 1
                if hour >= 24:
                    hour = 0
                if minutes > 59:
                    minutes = 59
                if seconds > 59:
                    seconds = 59

                # convert month, and do error trapping
                try:
                    wmonth = int(wmonth)
                except ValueError:
                    wmonth = _return_month(wmonth)
                if wmonth > 12:
                    wmonth = 12

                # get the number of days in wyear of all months
                numdays = [0] + [calendar.monthrange(year, month)[1] for year 
                    in [wyear] for month in range(1, 13) ]

            if wday > numdays[wmonth]:
                wday = numdays[wmonth]

            # ExifImage Year must be greater than 1900
            # if not, we save it as a string
            if wyear < 1900:
                wdate = "%04d-%s-%02d %02d:%02d:%02d" % (
                    wyear, _dd.long_months[wmonth], wday, hour, minutes, seconds)

            # year -> or equal to 1900
            else:
                wdate = datetime(wyear, wmonth, wday, hour, minutes, seconds)

            self.exif_widgets["NewDate"].set_text("%04d-%s-%02d" % (
                wyear, _dd.long_months[wmonth], wday) )
            self.exif_widgets["NewTime"].set_text("%02d:%02d:%02d" % (
                hour, minutes, seconds) )

        else:

            ErrorDialog(_("There was a problem with either the date and/ or time."))

        # return the modified date/ time
        return wdate

# -----------------------------------------------
#              Date Calendar functions
# -----------------------------------------------
    def select_date(self, obj):
        """
        will allow you to choose a date from the calendar widget
        """
 
        tip = _("Double click a date to return the date.")

        self.app = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.app.tooltip = tip
        self.app.set_title(_("Select Date"))
        self.app.set_default_size(450, 200)
        self.app.set_border_width(10)
        self.exif_widgets["Calendar"] = gtk.Calendar()
        self.exif_widgets["Calendar"].connect('day-selected-double-click', self.double_click)
        self.app.add(self.exif_widgets["Calendar"])
        self.exif_widgets["Calendar"].show()
        self.app.show()

    def double_click(self, obj):
        """
        receives double-clicked and returns the selected date to "NewDate"
        widget
        """

        year, month, day = self.exif_widgets["Calendar"].get_date()
        self.exif_widgets["NewDate"].set_text(
            "%04d-%s-%02d" % (year, _dd.long_months[month], day) )

        # close this window
        self.app.destroy()

# -------------------------------------------------------------------
#          GPS Coordinates functions
# -------------------------------------------------------------------
    def addsymbols2gps(self, latitude =False, longitude =False):
        """
        converts a degrees, minutes, seconds representation of Latitude/ Longitude
        without their symbols to having them...

        @param: latitude -- Latitude GPS Coordinates
        @param: longitude -- Longitude GPS Coordinates
        """
        LatitudeRef, LongitudeRef = "N", "E"

        # check to see if Latitude/ Longitude exits?
        if (latitude and longitude):

            if (latitude.count(".") == 1 and longitude.count(".") == 1):
                self.convert2dms(self.plugin_image)

                # get Latitude/ Longitude from data fields
                # after the conversion
                latitude  =  self.exif_widgets["Latitude"].get_text()
                longitude = self.exif_widgets["Longitude"].get_text()

            # add DMS symbols if necessary?
            # the conversion to decimal format, require the DMS symbols
            elif ( (latitude.count("°") == 0 and longitude.count("°") == 0) and
                (latitude.count("′") == 0 and longitude.count("′") == 0) and
                (latitude.count('″') == 0 and longitude.count('″') == 0) ):

                # is there a direction element here?
                if (latitude.count("N") == 1 or latitude.count("S") == 1):
                    latdeg, latmin, latsec, LatitudeRef = latitude.split(" ", 3)
                else:
                    atitudeRef = "N"
                    latdeg, latmin, latsec = latitude.split(" ", 2)
                    if latdeg[0] == "-":
                        latdeg = latdeg.replace("-", "")
                        LatitudeRef = "S"

                # is there a direction element here?
                if (longitude.count("E") == 1 or longitude.count("W") == 1):
                    longdeg, longmin, longsec, LongitudeRef = longitude.split(" ", 3)
                else:
                    ongitudeRef = "E"
                    longdeg, longmin, longsec = longitude.split(" ", 2)
                    if longdeg[0] == "-":
                        longdeg = longdeg.replace("-", "")
                        LongitudeRef = "W"

                latitude  = """%s° %s′ %s″ %s""" % (latdeg, latmin, latsec, LatitudeRef)
                longitude = """%s° %s′ %s″ %s""" % (longdeg, longmin, longsec, LongitudeRef)
        return latitude, longitude

    def convert2decimal(self, obj):
        """
        will convert a decimal GPS Coordinates into decimal format
        """

        # get Latitude/ Longitude from the data fields
        latitude  =  self.exif_widgets["Latitude"].get_text()
        longitude = self.exif_widgets["Longitude"].get_text()

        # if latitude and longitude exist?
        if (latitude and longitude):

            # is Latitude/ Longitude are in DMS format?
            if (latitude.count(" ") >= 2 and longitude.count(" ") >= 2): 

                # add DMS symbols if necessary?
                # the conversion to decimal format, require the DMS symbols 
                if ( (latitude.count("°") == 0 and longitude.count("°") == 0) and
                    (latitude.count("′") == 0 and longitude.count("′") == 0) and
                    (latitude.count('″') == 0 and longitude.count('″') == 0) ):

                    latitude, longitude = self.addsymbols2gps(latitude, longitude)

                # convert degrees, minutes, seconds w/ symbols to an 8 point decimal
                latitude, longitude = conv_lat_lon( unicode(latitude),
                                                    unicode(longitude), "D.D8")

                self.exif_widgets["Latitude"].set_text(latitude)
                self.exif_widgets["Longitude"].set_text(longitude)

    def convert2dms(self, obj):
        """
        will convert a decimal GPS Coordinates into degrees, minutes, seconds
        for display only
        """

        # get Latitude/ Longitude from the data fields
        latitude = self.exif_widgets["Latitude"].get_text()
        longitude = self.exif_widgets["Longitude"].get_text()

        # if Latitude/ Longitude exists?
        if (latitude and longitude):

            # if coordinates are in decimal format?
            if (latitude.count(".") == 1 and longitude.count(".") == 1):

                # convert latitude and longitude to a DMS with separator of ":"
                latitude, longitude = conv_lat_lon(latitude, longitude, "DEG-:")
 
                # remove negative symbol if there is one?
                LatitudeRef = "N"
                if latitude[0] == "-":
                    latitude = latitude.replace("-", "")
                    LatitudeRef = "S"
                latdeg, latmin, latsec = latitude.split(":", 2)

               # remove negative symbol if there is one?
                LongitudeRef = "E"
                if longitude[0] == "-":
                    longitude = longitude.replace("-", "")
                    LongitudeRef = "W"
                longdeg, longmin, longsec = longitude.split(":", 2)

                self.exif_widgets["Latitude"].set_text(
                    """%s° %s′ %s″ %s""" % (latdeg, latmin, latsec, LatitudeRef) )

                self.exif_widgets["Longitude"].set_text(
                    """%s° %s′ %s″ %s""" % (longdeg, longmin, longsec, LongitudeRef) )

def string_to_rational(coordinate):
    """
    convert string to rational variable for GPS
    """

    if '.' in coordinate:
        value1, value2 = coordinate.split('.')
        return pyexiv2.Rational(int(float(value1 + value2)), 10**len(value2))
    else:
        return pyexiv2.Rational(int(coordinate), 1)

def _removesymbols4saving(latitude =False, longitude =False):
    """
    will recieve a DMS with symbols and return it without them

    @param: latitude -- Latitude GPS Coordinates
    @param: longitude -- GPS Longitude Coordinates
    """

    # check to see if latitude/ longitude exist?
    if (latitude and longitude):

        # remove degrees symbol if it exist?
        latitude = latitude.replace("°", "")
        longitude = longitude.replace("°", "")

        # remove minutes symbol if it exist?
        latitude = latitude.replace("′", "")
        longitude = longitude.replace("′", "")

        # remove seconds symbol if it exist?
        latitude = latitude.replace('″', "")
        longitude = longitude.replace('″', "")

    return latitude, longitude

def coords_to_rational(Coordinates):
    """
    returns the GPS coordinates to Latitude/ Longitude
    """

    return [string_to_rational(coordinate) for coordinate in Coordinates.split( " ")]

def convert_value(value):
    """
    will take a value from the coordinates and return its value
    """

    return str( (Decimal(value.numerator) / Decimal(value.denominator)) )
