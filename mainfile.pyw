# -*- coding: utf-8 -*-
"""
Created on Mon Jun 22 16:43:18 2020

@author: halbauer
"""

'''
Autor: Halbauer
Date: 06.02.2019

Template zum Laden eines QT5 Fensters mit Tastaturkürzeln und Triggern

Erstellung des Layouts mit QT-Designer wird angenommen
Hierfür im Vorfeld .ui Datei in .py umwandlen und im gleichen VZ wie Template.py ablegen
Code für Umwandlung:
    pyuic5 -x template.ui -o template.py

'''
from PyQt5.QtWidgets import QMessageBox as QMB
from PyQt5 import QtCore, QtGui, QtWidgets
import umt_gui
import umt_filter as umt
import sys # We need sys so that we can pass argv to QApplication
from os.path import basename
import json

class UMT(QtWidgets.QMainWindow, umt_gui.Ui_UMT_Auswertung):
    def __init__(self):
        super(UMT, self).__init__()
        self.setupUi(self)
        self.statusBar().showMessage('Programm erfolgreich geladen.', 2000)
        self.setup_triggers()   # lade Events für Buttons

    def setup_triggers(self):
        self.but_debug.clicked.connect(self.debug)
        self.but_calc_s.clicked.connect(self.calc_friction_distance)
        self.but_export.clicked.connect(self.export_to_excel)
        self.but_clear_data.clicked.connect(self.clear_df)

        # Aus-/Einklappen
        self.but_collapse_export.clicked.connect(lambda: self.toggle_area(self.but_collapse_export))
        self.but_collapse_auto.clicked.connect(lambda: self.toggle_area(self.but_collapse_auto))
        self.but_collapse_settings.clicked.connect(lambda: self.toggle_area(self.but_collapse_settings))

        # Automation
        self.but_auto_prep.clicked.connect(self.auto_prepare_data)
        self.but_auto_filt.clicked.connect(self.auto_filter)
        self.but_auto_cof.clicked.connect(self.auto_cof)
        self.but_auto_export.clicked.connect(self.auto_export)


        # Radiobuttons
        self.rb_cof_t.toggled.connect(lambda: self.fill_rkf_bounds(self.rb_cof_t))
        self.rb_cof_s.toggled.connect(lambda: self.fill_rkf_bounds(self.rb_cof_s))
        self.rb_filt_sav.toggled.connect(lambda: self.enable_filters(self.rb_filt_sav))
        self.rb_filt_roll.toggled.connect(lambda: self.enable_filters(self.rb_filt_roll))
        self.rb_filt_med.toggled.connect(lambda: self.enable_filters(self.rb_filt_med))
        self.rb_export_red.toggled.connect(lambda: self.change_export_mode(self.rb_export_red))
        self.rb_export_n.toggled.connect(lambda: self.change_export_mode(self.rb_export_n))

        # Plotten
        self.but_plot_raw.clicked.connect(self.plot_raw)
        self.but_plot_min.clicked.connect(self.plot_minima)
        self.but_plot_dist.clicked.connect(self.plot_slope)
        self.but_plot_area.clicked.connect(self.plot_area)
        self.but_plot_filt.clicked.connect(self.plot_filter)
        self.but_plot_cof.clicked.connect(self.plot_cof)
        self.but_plot_export.clicked.connect(self.plot_export)

        # Toolbutton
        self.tool_output_file.clicked.connect(self.file_save)
        self.tool_input_file.clicked.connect(self.file_open)
        self.tool_output_pics.clicked.connect(lambda: self.folder_open(self.txt_output_pics))

        # Bestätigungen
        self.but_min_ok.clicked.connect(self.confirm_minima)
        self.but_dist_ok.clicked.connect(self.confirm_slope)
        self.but_area_ok.clicked.connect(self.confirm_area)
        self.but_filt_ok.clicked.connect(self.confirm_filter)
        self.but_cof_ok.clicked.connect(self.confirm_cof)

        # Aktionen
        self.actionOpen_File.triggered.connect(self.file_open)
        self.actionOpen_Folder.triggered.connect(self.folder_open)
        self.actionSpeichern.triggered.connect(self.save_settings)
        self.actionLaden.triggered.connect(self.load_settings)
        self.actionExport.triggered.connect(self.export_to_excel)
    
    # -----------------  Algorithmen -------------------
    def load_data(self):
        valid = self.validate_parameters()
        if not valid:
            return
        # Teste, ob Änderungen am Dateipfad vorgenommen wurden
        if self.fname == self.txt_input_file.text():
            fname = self.fname
        else: 
            fname = self.txt_input_file.text()
        try:
            df = umt.get_data(fname)
        except FileNotFoundError:
            return False

        self.compare_lists(df)

        return df

    def create_minima(self):
        if self.df is not None:
            # Lade Daten
            df = self.df
            # Bilde Absolutwerte
            df['Fx'] = df['Fx'].abs()
            # übernehme die Einstellungen
            try:
                self.un_highlight(self.txt_para_min_dist)
                dist = int(self.txt_para_min_dist.text())
            except ValueError:
                self.highlight_field(self.txt_para_min_dist)
                self.show_error_box('Der Punktabstand muss ganzzahlig sein!') 
                return False

            # Höhe muss mit -1 multipliziert werden, da minima als negative Maxima gesucht werden
            height = float(self.txt_para_min_thresh.text().replace(',','.'))*-1
            # finde die Minima
            loc_minima = umt.find_minima(df['Fx'].values, dist, height)
            self.minima = df.iloc[loc_minima]   
            # schreibe aus Absolutwerte geänderte Daten zurück
            self.df = df
            return True
        else:
            return False

    def find_slope(self):
        if self.minima is not None:
            # Daten laden
            minima = self.minima
            # Angabe des Grenzwerts in % erwartet
            thresh = float(self.txt_para_dist_thresh.text().replace(',','.'))*0.01
            # Offset für Datenanalyse
            try:
                self.un_highlight(self.txt_para_dist_off)
                self.off = int(self.txt_para_dist_off.text())
            except ValueError:
                self.highlight_field(self.txt_para_dist_off)
                self.show_error_box('Der Offset muss ganzzahlig sein!')
                return False

            self.dist, self.thresh_ind, self.cut = umt.find_einlauf(minima, thresh, self.off)
            return True
        else:
            return False

    def calc_slope(self):
        df = self.df
        minima = self.minima

        off = int(self.txt_para_dist_off.text().replace(',','.'))
        cut = self.cut
        thresh_ind = self.thresh_ind

        # Beschneide die geladenen Daten
        df_2 = df[df.Time >= cut]
        minima_2 = minima[:].iloc[thresh_ind+off:]

        # Schreibe die Werte fest in die Daten
        self.df_2 = df_2
        self.minima_2 = minima_2

    def cut_data(self):
        if self.df_2 is not None and self.minima_2 is not None:
            df_2 = self.df_2
            minima_2 = self.minima_2
            
            # Slice den Dataframe an den Stellen um die Minima
            to_cut = minima_2.index
            shift = int(self.txt_para_area_shift.text())

            # Erstelle Liste mit Indices aller gewünschter Werte
            liste2 = []
            for j in range(len(to_cut)-1):
                liste2 += [i for i in range(to_cut[j]+shift, to_cut[j+1]-shift)]

            # Bereinigte Daten von Fx
            df_3 = df_2[df_2.index.isin(liste2)]

            self.df_3 = df_3
            return True
        else: 
            return False

    def get_filtered_data(self):
        self.statusBar().showMessage('')
        if self.df_3 is not None:
            # Berechne den Reibkoeffizienten
            self.get_rkf_data()
            # Lade Daten als numpy array für bessere Kompatibilität
            unfiltered = self.df_3['RKF']
            # teste, welche Filtermethode gewählt wurde
            if self.rb_filt_sav.isChecked():
                filt = self.rb_filt_sav.text()
                n = int(self.txt_para_filt_n_sav.text())
                p = int(self.txt_para_filt_p_sav.text())
                #  Teste, ob n gerade ist
                if (n % 2) == 0:
                    self.highlight_field(self.txt_para_filt_n_sav)
                    self.statusBar().showMessage('Die Punktanzahl muss ungerade sein!')
                    return False, False
                else:
                    self.un_highlight(self.txt_para_filt_n_sav)

                # Teste, ob Grad des Polynoms größer als Anzahl ist
                if p >= n:
                    self.highlight_field(self.txt_para_filt_n_sav)
                    self.highlight_field(self.txt_para_filt_p_sav)
                    self.statusBar().showMessage('Grad des Polynoms muss kleiner als Punktanzahl sein!')
                    return False, False
                else:
                    self.un_highlight(self.txt_para_filt_n_sav)
                    self.un_highlight(self.txt_para_filt_p_sav)

                #  Teste, ob n gerade ist
                if n < 1:
                    self.highlight_field(self.txt_para_filt_n_sav)
                    self.statusBar().showMessage('Die Punktanzahl muss größer als 1 sein!')
                    return False, False
                else:
                    self.un_highlight(self.txt_para_filt_n_sav)

                # Filtere Daten
                filtered_data = umt.reduce_data(unfiltered.values, n, p)

            elif self.rb_filt_roll.isChecked():
                filt = self.rb_filt_roll.text()
                n = int(self.txt_para_filt_n_roll.text())

                filtered_data = umt.gleit_durch(unfiltered, n)

                #  Teste, ob n gerade ist
                if n < 1:
                    self.highlight_field(self.txt_para_filt_n_roll)
                    self.statusBar().showMessage('Die Punktanzahl muss größer als 1 sein!')
                    return False, False
                else:
                    self.un_highlight(self.txt_para_filt_n_roll)

            elif self.rb_filt_med.isChecked():
                filt = self.rb_filt_med.text()
                n = int(self.txt_para_filt_n_med.text())

                #  Teste, ob n gerade ist
                if n < 1:
                    self.highlight_field(self.txt_para_filt_n_med)
                    self.statusBar().showMessage('Die Punktanzahl muss größer als 1 sein!')
                    return False, False
                else:
                    self.un_highlight(self.txt_para_filt_n_med)

                #  Teste, ob n gerade ist
                if (n % 2) == 0:
                    self.highlight_field(self.txt_para_filt_n_med)
                    self.statusBar().showMessage('Die Punktanzahl sollte ungerade sein!')
                    return False, False
                else:
                    self.un_highlight(self.txt_para_filt_n_med)

                filtered_data = umt.median_filt(unfiltered, n)

            return filt, filtered_data
        else:
            return False, False

    def calc_friction_distance(self):
        valid = self.validate_parameters()
        if not valid:
            return False
        self.statusBar().showMessage('')
        if self.txt_para_hub.text() == '':
            self.statusBar().setStyleSheet('color:red; font-weight:bold')
            self.highlight_field(self.txt_para_hub)
            self.statusBar().showMessage('Kein Hub angegeben!')
            # self.highlight_field(self.txt_input_file)
            return False
        else:
            self.un_highlight(self.txt_para_hub)

        if self.txt_para_frequency.text() == '':
            self.statusBar().setStyleSheet('color:red; font-weight:bold')
            self.highlight_field(self.txt_para_frequency)
            self.statusBar().showMessage('Keine Frequenz angegeben!')
            # self.highlight_field(self.txt_input_file)
            return False
        else:
            self.un_highlight(self.txt_para_frequency)
        
        try:
            df = self.df_3
            mode = 3
        except AttributeError:
            try:
                df = self.df_2
                mode = 2
            except AttributeError:
                try:
                    df = self.df
                    mode = 1
                except AttributeError:
                    self.statusBar().showMessage('Hier stimmt etwas gewaltig nicht.', 10000)
                    return


        if df is not None:
            hub = float(self.txt_para_frequency.text())
            freq = float(self.txt_para_hub.text())

            data = (hub * freq * df['Time'] *2) / 1000
            df = df.assign(V_weg = data)

            self.compare_lists(df)

            if mode == 3:
                self.df_3 = df
            elif mode == 2:
                self.df_2 = df
            elif mode == 1:
                self.df = df

            return True
        else:
            return False
  
    def get_rkf_data(self):
        if self.df_3 is not None:
            pass
        else:
            return
        df = self.df_3

        cof = df['Fx']/df['Fz']
        df = df.assign(RKF = cof)

        self.compare_lists(df)

        self.df_3 = df

    def fill_rkf_bounds(self, b):
        if b.text() == "x = t":
            if b.isChecked() == True:
                self.lab_cof_start.setText('s')
                self.lab_cof_end.setText('s')
                # hier wird ein Wert von 10 als Offset zum letzten Wert gewählt...
                ende = self.df_3['Time'].iloc[-10]
                self.txt_para_cof_end.setText(f'{round(ende, 2)}')
                
				
        if b.text() == "x = s":
            if b.isChecked() == True:
                self.txt_para_cof_end.setText('')
                self.lab_cof_start.setText('m')
                self.lab_cof_end.setText('m')
                if 'V_weg' in self.df_3.columns:
                    # hier wird ein Wert von 10 als Offset zum letzten Wert gewählt...
                    ende = self.df_3['V_weg'].iloc[-10]
                else:
                    ret = self.calc_friction_distance()
                    if ret:
                        # hier wird ein Wert von 10 als Offset zum letzten Wert gewählt...
                        ende = self.df_3['V_weg'].iloc[-10]
                    else: 
                        ende = ''
                        return
                
                self.txt_para_cof_end.setText(f'{round(ende, 2)}')
        self.txt_para_cof_start.setText('')


    def calc_rkf(self):
        self.statusBar().showMessage('')
        if self.df_3 is not None:
            df = self.df_3
            # Berechnung Reibungskoeffizient
            try:
                x_start = float(self.txt_para_cof_start.text())
            except ValueError:
                self.show_error_box('Bitte Startpunkt für Koeffizientenberechnung angeben.')
                return
            try:
                x_end = float(self.txt_para_cof_end.text())
            except ValueError:
                self.show_error_box('Bitte Endpunkt für Koeffizientenberechnung angeben.')
                return
            # Arbeite mit Zeitdaten
            if self.rb_cof_t.isChecked():
                s = 'Time'
            # Arbeite mit Wegdaten
            if self.rb_cof_s.isChecked():
                s = 'V_weg'
           
            idx_rkf_strt = df[s].loc[df[s] <= x_start].index[-1]
            idx_rkf_end = df[s].loc[df[s] <= x_end].index[-1]


            # plotte die Originaldaten und die gefilterten Daten
            # add_data(df, series, 'savgol')
            rkf_stat = df['RKF'].loc[idx_rkf_strt:idx_rkf_end].mean()
            
            return rkf_stat

        else:
            return

    def export_to_excel(self):
        valid = self.validate_parameters()
        if not valid:
            return False

        cols_to_export = self.get_cols()
        if not cols_to_export:
            self.show_error_box('Es wurden keine Spalten zum Exportieren ausgewählt.')
            return

        savepath = str(self.txt_output_file.text())

        if savepath == '':
            answer = self.show_msg_box('Es wurde kein Speicherort angegeben.\nFortfahren?')
            if not answer:
                return

        try:
            df = self.df_3
        except AttributeError:
            try:
                df = self.df_2
            except AttributeError:
                try:
                    df = self.df
                except AttributeError:
                    self.statusBar().showMessage('Hier stimmt etwas gewaltig nicht.', 10000)
                    return

        df = df[cols_to_export]
        
        n = self.get_reduction(df)
        
        df = df[::n]

        # Zeige Speichergröße an
        # df.info(memory_usage='deep')

        umt.save_as_xls(df, savepath)

        self.show_info_box('Datei erfolgreich exportiert')

    # ------------------ Automation -------------------------
    def auto_prepare_data(self):
        valid = self.validate_parameters()
        if not valid:
            self.show_error_box('Es wurde keine Datei angegeben!')
            return False
        try:
            self.df = self.load_data()
        except FileNotFoundError:
            self.show_error_box('Datei nicht gefunden')
            return False

        self.create_minima()
        self.find_slope()
        self.calc_slope()
        self.cut_data()
        # ab hier existiert df_3
        return True
    
    def auto_filter(self):
        try:
            df = self.df_3
        except AttributeError:
            ret = self.auto_prepare_data()
            if not ret:
                return False
            
        filt, fdata = self.get_filtered_data()
        if not filt:
            return
        else:
            df = self.df_3

        df = df.assign(COF_gefiltert = fdata)

        self.compare_lists(df)

        self.df_3 = df

        return True

    def auto_cof(self):
        try:
            df = self.df_3
        except AttributeError:
            ret = self.auto_filter()
            if not ret:
                return False
            else:
                df = self.df_3
        
        self.get_rkf_data()

        ret = self.calc_friction_distance()
        if not ret:
            return False
        

        cof = self.calc_rkf()

        if not cof:
            return False

        df = df.assign(stat_cof = cof)

        self.df_3 = df

        return True

    def auto_export(self):
        try:
            df = self.df_3
        except AttributeError:
            ret = self.auto_cof()
            if not ret:
                return
            else:
                df = self.df_3

        savepath = str(self.txt_output_file.text())

        if savepath == '':
            answer = self.show_msg_box('Es wurde kein Speicherort angegeben.\nFortfahren?')
            if not answer:
                return
        

        n = self.get_reduction()
        
        # es wird mit allen Daten gearbeitet
        df = df[::n]

        # Zeige Speichergröße an
        # df.info(memory_usage='deep')

        umt.save_as_xls(df, savepath)

        self.show_info_box('Datei erfolgreich exportiert')


    # --------------  Plotfunktionen  ------------------    
    def plot_raw(self):
        df = self.load_data()
        save = self.cb_save_pic_raw.isChecked()
        savepath = self.txt_output_pics.text()

        # Wenn kein Speicherverzeichnis angegeben ist
        if save and savepath == '':
            answer = self.show_msg_box('Es ist kein Speicherort für die Bilder definiert.\nSpeichere im Programmverzeichnis.')
            if not answer:
                return 
        if df is not None: 
            umt.plot_data(df['Time'], df['Fx'], save=save, pic_path=savepath)
        else:
            return

    def plot_minima(self):
        valid = self.validate_parameters()
        if not valid:
            return
        
        if self.create_minima():
            pass
        else:
            return

        df = self.df
        minima = self.minima

        try:
            anz = int(self.txt_para_min_n.text())
        except ValueError:
            anz = None
        try:
            pos_list = [i.replace(',', '.') for i in self.txt_para_min_pos.text().split('; ')]
            pos = list(map(float, pos_list))

        except ValueError:
            pos = None

        self.statusBar().showMessage('')
        if not any([anz, pos]):
            self.highlight_field(self.txt_para_min_n)
            self.highlight_field(self.txt_para_min_pos)
            self.statusBar().showMessage('Keine Parameter angegeben!')
            return False
        if pos and anz != len(pos):
            self.highlight_field(self.txt_para_min_n)
            self.highlight_field(self.txt_para_min_pos)
            self.statusBar().showMessage('Anzahl Positionen und Messstellen ist nicht gleich')
            return False
        else:
            self.un_highlight(self.txt_para_min_n)
            self.un_highlight(self.txt_para_min_pos)

        if not pos:
            rand = True
        else:
            rand = False

        save = self.cb_save_pic_min.isChecked()
        savepath = self.txt_output_pics.text()

        if save and savepath == '':
            answer = self.show_msg_box('Es ist kein Speicherort für die Bilder definiert.\nSpeichere im Programmverzeichnis.')
            if not answer:
                return 

        umt.test_minima(df, minima, pos=pos, rand=rand, anz=anz, save=save, p_path=savepath) 

    def plot_slope(self):
        df = self.df
        # Hole die aktuellen Daten ab
        if self.find_slope():
            pass
        else:
            return 

        minima = self.minima
        dist = self.dist
        thresh_ind = self.thresh_ind
        cut = self.cut
        off = self.off
        
        save = self.cb_save_pic_dist.isChecked()
        savepath = self.txt_output_pics.text()

        # Wenn kein Speicherverzeichnis angegeben ist
        if save and savepath == '':
            answer = self.show_msg_box('Es ist kein Speicherort für die Bilder definiert.\nSpeichere im Programmverzeichnis.')
            if not answer:
                return 

        # teste den Einlauf mit den aktuellen Einstellungen 
        umt.test_einlauf(df, dist, minima, thresh_ind, off, cut, save, savepath) 

    def plot_area(self):
        if self.cut_data():
            pass
        else: 
            return

        df_2 = self.df_2
        minima_2 = self.minima_2


        try:
            anz = int(self.txt_para_area_n.text())
        except ValueError:
            anz = None
        try:
            pos_list = [i.replace(',', '.') for i in self.txt_para_area_pos.text().split('; ')]
            pos = list(map(float, pos_list))

        except ValueError:
            pos = None

        self.statusBar().showMessage('')
        if not any([anz, pos]):
            self.highlight_field(self.txt_para_area_n)
            self.highlight_field(self.txt_para_area_pos)
            self.statusBar().showMessage('Keine Parameter angegeben!')
            return False
        if pos and anz != len(pos):
            self.highlight_field(self.txt_para_area_n)
            self.highlight_field(self.txt_para_area_pos)
            self.statusBar().showMessage('Anzahl Positionen und Messstellen ist nicht gleich')
            return False
        else:
            self.un_highlight(self.txt_para_area_n)
            self.un_highlight(self.txt_para_area_pos)

        if not pos:
            rand = True
        else:
            rand = False

        shift = int(self.txt_para_area_shift.text())

        save = self.cb_save_pic_area.isChecked()
        savepath = self.txt_output_pics.text()

        # Wenn kein Speicherverzeichnis angegeben ist
        if (save == True) and (savepath == ''):
            answer = self.show_msg_box('Es ist kein Speicherort für die Bilder definiert.\nSpeichere im Programmverzeichnis.')
            if not answer:
                return 

        # Teste, ob Versatz korrekt eingestellt ist
        umt.test_area(df_2, minima_2, patch_pos=pos, shift=shift, pcount=anz, rand_patch=rand, save=save, p_path=savepath)

    def plot_filter(self):
        if self.df_3 is not None:
            pass
        else: 
            return
        
        filt, fdata = self.get_filtered_data()
        if not filt:
            return

        df = self.df_3

        if self.rb_filt_med.isChecked() or self.rb_filt_sav.isChecked():
            x2 = df['Time']
        if self.rb_filt_roll.isChecked():
            anz = int(self.txt_para_filt_n_roll.text())-1
            x2 = df['Time'].iloc[:-anz]

        save = self.cb_save_pic_filt.isChecked()
        savepath = self.txt_output_pics.text()

        # Wenn kein Speicherverzeichnis angegeben ist
        if (save == True) and (savepath == ''):
            answer = self.show_msg_box('Es ist kein Speicherort für die Bilder definiert.\nSpeichere im Programmverzeichnis.')
            if not answer:
                return 

        umt.plot_data(df['Time'], df['RKF'], x2, fdata, ptype='filtered',save=save, filter=filt, pic_path=savepath)

    def plot_cof(self):
        if self.df_3 is not None:
            pass
        else: 
            return

        # wenn Verschleißweg noch nicht berechnet ist, 
        if self.rb_cof_s.isChecked():
            ret = self.calc_friction_distance()
            if ret:
                pass
            else: 
                self.show_error_box('Zur Berechnung des Verschleißweges fehlen noch Eingaben!')
                return

        # Wenn keine Grenzen angeben sind
        if self.txt_para_cof_start.text() == '':
            answer = self.show_msg_box('Es ist kein Startpunkt für die Berechnung von COF definiert.\nGebe die gefilterten Daten aus.')
            if not answer:
                return
            else:
                modus = 'filtered'
        else:
            modus = 'rkf'
            y_rkf = self.calc_rkf()

        filt, fdata = self.get_filtered_data()

        df = self.df_3

        save = self.cb_save_pic_cof.isChecked()
        savepath = self.txt_output_pics.text()

        # Wenn kein Speicherverzeichnis angegeben ist
        if (save == True) and (savepath == ''):
            answer = self.show_msg_box('Es ist kein Speicherort für die Bilder definiert.\nSpeichere im Programmverzeichnis.')
            if not answer:
                return 

        # setze die zu plottenden Rohdaten gemäß der Auswahl
        if self.rb_cof_t.isChecked():
            x = df['Time']
        elif self.rb_cof_s.isChecked():
            # Wenn Verschleißweg schon berechnet wurde
            if 'V_weg' in df.columns:
                x = df['V_weg']
            else:
                # Berechne den Verschleißweg und setze ihn als x-Werte
                valid = self.calc_friction_distance()
                if not valid:
                    return
                df = self.df_3
                x = df['V_weg']
        
        # passe die gefilterten X-Werte an, falls andere Filter ausgewählt sind.
        if self.rb_filt_med.isChecked() or self.rb_filt_sav.isChecked():
            x2 = x
        if self.rb_filt_roll.isChecked():
            anz = int(self.txt_para_filt_n_roll.text())-1
            x2 = x.iloc[:-anz]



        if modus == 'filtered':
            umt.plot_data(x, df['RKF'], x2, fdata, ptype='filtered',save=save, filter=filt, pic_path=savepath)
        elif modus == 'rkf':
            umt.plot_data(x, df['RKF'], x2, fdata, ptype='filtered',save=save, filter=filt, pic_path=savepath, rkf=y_rkf)

    def plot_export(self):
        # teste, ob schon Daten vorhanden sind
        valid = self.validate_parameters()
        if not valid:
            return

        cols_to_plot = self.get_cols()
        if not cols_to_plot:
            self.show_error_box('Es wurden keine Spalten zum plotten ausgewählt.')
            return

        if len(cols_to_plot) > 2:
            self.show_error_box('Es können aktuell nicht mehr als 2 Spalten zum Plotten ausgewählt werden.\nBitte wähle Spalten ab.')
            return
        
        if not any(x in cols_to_plot for x in ['Time', 'V_weg']):
            self.show_error_box('Fehlerhafte x-Werte.\nBitte wähle die Spalte "Time" oder "V_weg" aus.')
            return
        
        if cols_to_plot == ['Time', 'V_weg']:
            self.show_error_box('Das ergibt eine Gerade.\nBitte wähle die Spalte "Time" ODER "V_weg" aus.')
            return

        try:
            df = self.df_3
        except AttributeError:
            try:
                df = self.df_2
            except AttributeError:
                try:
                    df = self.df
                except AttributeError:
                    self.statusBar().showMessage('Hier stimmt etwas gewaltig nicht.', 10000)
                    return

        save = self.cb_save_pic_cof.isChecked()
        savepath = self.txt_output_pics.text()

        # Wenn kein Speicherverzeichnis angegeben ist
        if (save == True) and (savepath == ''):
            answer = self.show_msg_box('Es ist kein Speicherort für die Bilder definiert.\nSpeichere im Programmverzeichnis.')
            if not answer:
                return 


        df = df[cols_to_plot]

        if 'V_weg' in df.columns:
            x = df['V_weg']
            cols_to_plot.remove('V_weg')
            y = df[cols_to_plot[0]]
        else:
            x = df['Time']
            cols_to_plot.remove('Time')
            y = df[cols_to_plot[0]]

        if self.rb_filt_roll.isChecked():
            anz = int(self.txt_para_filt_n_roll.text())-1
            x = x.iloc[:-anz]

        n = self.get_reduction(x)

        x2 = x[::n]
        y2 = y[::n] 

        umt.plot_data(x, y, x2, y2, ptype='export', save=save, pic_path=savepath)


    # ------------------  Bestätigungen ---------------------
    def confirm_minima(self):
        valid = self.validate_parameters()
        if not valid:
            return
        self.create_minima()
        self.gb_dist.setEnabled(True)

    def confirm_slope(self):
        if self.find_slope():
            pass
        else:
            return 
        
        self.calc_slope()

        self.gb_area.setEnabled(True)
     
    def confirm_area(self):
        if self.cut_data():
            pass
        else: 
            return
        self.gb_filter.setEnabled(True)

    def confirm_filter(self):
        if self.df_3 is not None:
            pass
        else: 
            return
        
        filt, fdata = self.get_filtered_data()
        if not filt:
            return

        df = self.df_3

        df = df.assign(COF_gefiltert = fdata)
        # df.loc[:, 'COF_gefiltert'] = fdata

        self.compare_lists(df)

        self.df_3 = df

        self.gb_cof.setEnabled(True)
        self.fill_rkf_bounds(self.rb_cof_t)

    def confirm_cof(self):
        try:
            df = self.df_3
        except AttributeError:
            self.show_error_box('Die Daten sind noch nicht vorbereitet.\nVersuche die automatische Filterung.')
            return
        
        self.get_rkf_data()

        self.calc_friction_distance()

        cof = self.calc_rkf()

        df = df.assign(stat_cof = cof)

        self.df_3 = df

    # ------------------- Hilfsfunktionen ------------------------
    def clear_df(self):
        # Lösche Daten
        self.df_2 = None
        self.df_3 = None
        # lade Daten neu
        self.df = self.load_data()
        self.disable_settings()

    def disable_settings(self):
        self.gb_cof.setEnabled(False)
        self.gb_filter.setEnabled(False)
        self.gb_area.setEnabled(False)
        self.gb_dist.setEnabled(False)

    def get_frequency(self, fname):
        def find_hz_in_fname(fname, row, raw=False, splitter='_'):
            with open(fname, 'r') as f:
                for i, line in enumerate(f):
                    if i == row:
                        if raw:
                            line2 = r'{}'.format(line)
                        else:
                            line2 = line
                        headlist = line2.split(splitter)
                    if i > row:
                        break
            return headlist

        # lese erste Zeile ein
        with open(fname, 'r') as f:
            firstline = f.readline()

        # Wenn es sich um alte Daten handelt
        if 'Data File' in firstline:
            # Lese reduzierte Daten ein
            liste = find_hz_in_fname(fname, 1, raw=True)
            hz = float([i for i  in liste if 'Hz' in i][0].replace('Hz', '').replace(',', '.'))

            self.txt_para_frequency.setText(f'{hz}')

        # Wenn es neuer Daten sind
        elif 'Data Viewer' in firstline:
            liste = find_hz_in_fname(fname, 14, splitter='=')

            hz = float(liste[1].replace(',','.'))

            if hz > 30:
                self.show_error_box('In dieser Datei wurde wahrscheinlich die Geschwindigkeit angegeben.\nPasse Daten an.')
                
                liste = find_hz_in_fname(fname, 5, raw=True)
                hz2 = float([i for i  in liste if 'Hz' in i][0].replace('Hz', '').replace(',', '.'))

                self.txt_para_frequency.setText(f'{hz2}')

            else:
                self.txt_para_frequency.setText(f'{hz}')

        # Sonst sage, dass du die Daten nicht kennst und gebe nichts zurück
        else: 
            self.show_error_box('Das Datenformat kenne ich nicht.\nWähle eine andere Datei.')
            return

    def compare_lists(self, df):
        liste = [i for i in df.columns]

        lw = self.list_data
        # let lw haven elements in it.
        items = []
        for x in range(lw.count()-1):
            items.append(lw.item(x))

        # Wenn die aktuellen Labels gleich sind
        if items == liste:
            pass
        # Wenn gleich viele Labels aber unterschiedlicher Text
        elif len(items) == len(liste):
            # iteriere über alle Labels
            for i in range(len(items)):
                item = self.list_data.item(i)
                # Ändere Text nur, wenn verschieden
                if item.text() != liste[i]:
                    item.setText(liste[i])
        else: 
            self.list_data.clear()
            for i in liste:
                item = QtWidgets.QListWidgetItem(i)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.Unchecked)
                self.list_data.addItem(item)

    def enable_filters(self, b):
        n_sav = self.txt_para_filt_n_sav
        p_sav = self.txt_para_filt_p_sav
        n_roll = self.txt_para_filt_n_roll
        n_med = self.txt_para_filt_n_med
        l_n_sav = self.lab_n_sav
        l_p_sav = self.lab_p_sav
        l_n_roll = self.lab_n_roll
        l_n_med = self.lab_n_med
        if b.text() == 'Savgol-Filter' and b.isChecked():
            n_sav.setEnabled(True)
            p_sav.setEnabled(True)
            l_n_sav.setEnabled(True)
            l_p_sav.setEnabled(True)
            n_med.setEnabled(False)
            l_n_med.setEnabled(False)
            n_roll.setEnabled(False)
            l_n_roll.setEnabled(False)

        if b.text() == 'Gleitender Durchschnitt' and b.isChecked():            
            n_sav.setEnabled(False)
            p_sav.setEnabled(False)
            l_n_sav.setEnabled(False)
            l_p_sav.setEnabled(False)
            n_med.setEnabled(False)
            l_n_med.setEnabled(False)
            n_roll.setEnabled(True)
            l_n_roll.setEnabled(True)
            
        if b.text() == 'Median-Filter' and b.isChecked():
            n_sav.setEnabled(False)
            p_sav.setEnabled(False)
            l_n_sav.setEnabled(False)
            l_p_sav.setEnabled(False)
            n_med.setEnabled(True)
            l_n_med.setEnabled(True)
            n_roll.setEnabled(False)
            l_n_roll.setEnabled(False)

    def change_visibility(self, *fields):
        for f in list(fields):
            if f is None:
                continue
            if f.isEnabled():
                vis = False
            else:
                vis = True
            f.setEnabled(vis)

    def save_settings(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Speicherort für Einstellungen wählen.', '', 'JSON-Dateien (*.json);;All Files (*)')[0]
        if not fname:
            return

        if self.rb_filt_sav.isChecked():
            filt = 'Savgol'
        if self.rb_filt_roll.isChecked():
            filt = 'Rolling'
        if self.rb_filt_med.isChecked():
            filt = 'Median'

        if self.rb_cof_t.isChecked():
            coef_mode = 'Time'
        if self.rb_cof_s.isChecked():
            coef_mode = 'Weg'

        if self.rb_export_n.isChecked():
            red_mode = 'Anzahl'
        if self.rb_export_red.isChecked():
            red_mode = 'Faktor'

        sett = {
            'th_min' : self.txt_para_min_thresh.text(),
            'dist_min' : self.txt_para_min_dist.text(),
            'anz_min' : self.txt_para_min_n.text(),
            't_dist' : self.txt_para_dist_thresh.text(),
            'off_dist' : self.txt_para_dist_off.text(),
            'shift' : self.txt_para_area_shift.text(),
            'anz_area' : self.txt_para_area_shift.text(),
            'Filter' : filt,
            'n_sav' : self.txt_para_filt_n_sav.text(),
            'p_sav' : self.txt_para_filt_p_sav.text(),
            'n_roll' : self.txt_para_filt_n_roll.text(),
            'n_med' : self.txt_para_filt_n_med.text(),
            'COF-Mode' : coef_mode,
            'cof_start' : self.txt_para_cof_start.text(),
            'cof_end' : self.txt_para_cof_end.text(),

            'RED-Mode' : red_mode,
            'fak_red' : self.txt_para_exp_red.text(),
            'anz_red' : self.txt_para_exp_n.text(),

            # optionale Parameter
            'pos_min' : self.txt_para_min_pos.text(),
            'pos_area' : self.txt_para_area_pos.text(),

            'pic_path' : self.txt_output_pics.text(),
            'export_path' : self.txt_output_file.text(),
        }
        with open(fname, 'w') as json_file:
            json.dump(sett, json_file)
        
        self.show_info_box('Konfiguration erfolgreich gesichert.')

    def load_settings(self, fname):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Wähle eine Quelldatei', filter='*.json')[0]
        if not fname:
            return
        with open(fname) as json_file:
            data = json.load(json_file)

        self.txt_para_min_thresh.setText(data['th_min'])
        self.txt_para_min_dist.setText(data['dist_min'])
        self.txt_para_min_n.setText(data['anz_min'])
        self.txt_para_dist_thresh.setText(data['t_dist'])
        self.txt_para_dist_off.setText(data['off_dist'])
        self.txt_para_area_shift.setText(data['shift'])
        self.txt_para_area_shift.setText(data['anz_area'])
        if data['Filter'] == 'Savgol':
            self.rb_filt_sav.setChecked(True)
            self.rb_filt_roll.setChecked(False)
            self.rb_filt_med.setChecked(False)
        if data['Filter'] == 'Rolling':
            self.rb_filt_sav.setChecked(False)
            self.rb_filt_roll.setChecked(True)
            self.rb_filt_med.setChecked(False)
        if data['Filter'] == 'Median':
            self.rb_filt_sav.setChecked(False)
            self.rb_filt_roll.setChecked(False)
            self.rb_filt_med.setChecked(True)
                

        self.txt_para_filt_n_sav.setText(data['n_sav']),
        self.txt_para_filt_p_sav.setText(data['p_sav']),
        self.txt_para_filt_n_roll.setText(data['n_roll']),
        self.txt_para_filt_n_med.setText(data['n_med']),
        if data['COF-Mode'] == 'Time':
            self.rb_cof_t.setChecked(True)
            self.rb_cof_s.setChecked(False)
        if data['COF-Mode'] == 'Weg':
            self.rb_cof_t.setChecked(False)
            self.rb_cof_s.setChecked(True)

        self.txt_para_cof_start.setText(data['cof_start']),
        self.txt_para_cof_end.setText(data['cof_end']),

        if data['RED-Mode'] == 'Anzahl':
            self.rb_export_n.setChecked(True)
            self.rb_export_red.setChecked(False)
        if data['RED-Mode'] == 'Faktor':
            self.rb_export_n.setChecked(False)
            self.rb_export_red.setChecked(True)

        self.txt_para_exp_red.setText(data['fak_red']),
        self.txt_para_exp_n.setText(data['anz_red']),

        # optionale Parameter
        self.txt_para_min_pos.setText(data['pos_min']),
        self.txt_para_area_pos.setText(data['pos_area']),

        self.txt_output_pics.setText(data['pic_path']),
        self.txt_output_file.setText(data['export_path']),

        self.show_info_box('Konfiguration erfolgreich geladen!')

    def change_export_mode(self, b):
        if b.text() == 'Reduzierung':
            self.txt_para_exp_red.setEnabled(True)
            self.lab_export_red.setEnabled(True)
            self.txt_para_exp_n.setEnabled(False)
        if b.text() == 'Punkte':
            self.txt_para_exp_red.setEnabled(False)
            self.lab_export_red.setEnabled(False)
            self.txt_para_exp_n.setEnabled(True)

    def get_cols(self):
        liste = []
        for i in range(self.list_data.count()):
            if self.list_data.item(i).checkState() == QtCore.Qt.Checked:
                liste.append(str(self.list_data.item(i).text()))
        return liste

    def get_reduction(self, x=None):
        #  Hier werden die Daten reduziert
        if self.rb_export_red.isChecked():
            # passe die gefilterten X-Werte an, falls andere Filter ausgewählt sind.
            n = int(self.txt_para_exp_red.text())    
        else:
            angestrebte_punkte = int(self.txt_para_exp_n.text())
            n = int(round(len(x)/angestrebte_punkte,0))

        return n

    def proc_path(self, receiver, text):
        # Hier wird der Pfad in das Textfeld des 'receivers' geschrieben
        receiver.setText(text)

    def un_highlight(self, field):
        field.setStyleSheet('border: 1px solid black')
        self.statusBar().setStyleSheet('color:black; font-weight:normal')

    def highlight_field(self, field):
        field.setStyleSheet('border: 2px solid red;')   
        self.statusBar().setStyleSheet('color:red; font-weight:bold') 

    def validate_parameters(self):
        self.statusBar().showMessage('')
        if self.txt_input_file.text() == '':
            self.highlight_field(self.txt_input_file)
            self.statusBar().showMessage('Keine Quelldatei angegeben!')
            return False
        else:
            self.un_highlight(self.txt_input_file)


        return True

    def file_save(self):
        out_file = QtWidgets.QFileDialog.getSaveFileName(self, 'Speicherort wählen', '', 'Excel-Files (*.xlsx);;All Files (*)')[0]
        if not out_file:
            return
        self.proc_path(self.txt_output_file, out_file)

    def file_open(self):
        self.un_highlight(self.txt_input_file)
        self.fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Wähle eine Quelldatei', filter='*.txt')[0]
        if not self.fname:
            return
        #  Setze den Pfad in die Felder ein
        self.proc_path(self.txt_input_file, self.fname)
        # Ziehe die Frequenz oder die Geschwindigkeit aus den Daten
        self.get_frequency(self.fname)
        self.df = self.load_data()
        self.statusBar().showMessage('Datei erfolgreich geladen', 2000)

    def folder_open(self, dest):
        self.un_highlight(dest)
        path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Wähle einen Quellordner')
        if not path:
            return
        self.proc_path(dest, path)
        self.statusBar().showMessage('Ordner erfolgreich geladen', 2000)
             
    def debug(self):
        '''
            In diese Funktion kommt alles rein, was gerade getestet werden soll
        '''
        return

    def show_msg_box(self, text='Dies ist eine Warnung.'):
        msg = QMB()   
        msg.setWindowTitle("Warnung")
        msg.setText(text)
        msg.setIcon(QMB.Warning)
        msg.setStandardButtons(QMB.Cancel | QMB.Ok)
        msg.setDefaultButton(QMB.Ok)

        returnValue = msg.exec()
        if returnValue == QMB.Ok:
            press = True
        else:
            press = False

        return press

    def show_error_box(self, text='Fehler'):
        msg = QMB()   
        msg.setWindowTitle("Hinweis")
        msg.setText(text)
        msg.setIcon(QMB.Critical)
        msg.setStandardButtons(QMB.Ok)
        msg.setDefaultButton(QMB.Ok)

        msg.exec()

    def show_info_box(self, text='Info'):
        msg = QMB()   
        msg.setWindowTitle("Information")
        msg.setText(text)
        msg.setIcon(QMB.Information)
        msg.setStandardButtons(QMB.Ok)
        msg.setDefaultButton(QMB.Ok)

        msg.exec()

    def toggle_area(self, but):
        if but == self.but_collapse_export:
            area = self.scroll_export
            max_height = 180
        if but == self.but_collapse_settings:
            area = self.scroll_settings
            max_height = 292
        if but == self.but_collapse_auto:
            area = self.scroll_auto
            max_height = 200

        area_height = area.geometry().height()
        win_height_akt = self.centralwidget.geometry().height() 
        win_width_akt = self.centralwidget.geometry().width()


        if 'Verstecke' in but.text(): 
            new_text = but.text().replace('Verstecke ', 'Zeige ')
            area.setMaximumHeight(0)    
            new_win_height = win_height_akt - area_height
            # self.centralwidget.setFixedHeight(win_height_akt - area_height)
            
        if 'Zeige' in but.text():
            new_text = but.text().replace('Zeige ', 'Verstecke ')
            area.setMaximumHeight(max_height)
            new_win_height = win_height_akt + max_height
            # self.centralwidget.setFixedHeight()
            
        self.resize(win_width_akt, new_win_height)
        but.setText(new_text)

def main():
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    form = UMT()             # We set the form to be our ExampleApp (bsp1)
    form.show()                         # Show the form
    sys.exit(app.exec_())                         # and execute the app

if __name__ == '__main__':
    main()