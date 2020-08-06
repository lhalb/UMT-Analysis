import pandas as pd
import numpy as np
from scipy.signal import savgol_filter as sf
from scipy.signal import butter, filtfilt, argrelextrema, find_peaks, medfilt
import matplotlib
matplotlib.use('QT5Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import random
import os

def get_data(fname):
    # lese erste Zeile ein
    with open(fname, 'r') as f:
        firstline = f.readline()

    # Wenn es sich um alte Daten handelt
    if 'Data File' in firstline:
        # Lese reduzierte Daten ein
        skr = 5
        headline = 3

    # Wenn es neuer Daten sind
    elif 'Data Viewer' in firstline:
        skr = 23
        headline = 20

    # Sonst sage, dass du die Daten nicht kennst und gebe nichts zurück
    else: 
        print('Die angegebene Datei kann nicht gelesen werden.')
        return
    
    # Lese die festgelegte Zeile für die Spaltenbeschriftung ein
    with open(fname, 'r') as f:
        for i, line in enumerate(f):
            if i == headline:
                headlist = line.split()
            if i > headline:
                break
        
    # Lese die Daten ein ohne Überschriften
    df = pd.read_csv(fname, header=None, delimiter=' ', skipinitialspace=True, skiprows=skr)

    # korrigiere den Namen der Zeitspalte, falls aktuellere Daten eingelesen werden
    if 'T' in headlist:
        idx = headlist.index('T')
        headlist[idx] = 'Time'

    # Spalten benennen, fuer bessere Uebersicht
    header = {i : headlist[i] for i in range(0, len(headlist))}
    df.rename(columns=header, inplace=True)

    return df

def plot_data(x, y, x2=None, y2=None, ptype='original', boundaries=[[1.5,6], [0,6]], save=False, **kwargs):
    def save_func(x, ptype, dargs):
        if save:
            if len(x) > 10000:
                matplotlib.rcParams['agg.path.chunksize'] = 1000
            if 'pic_path' in dargs.keys():
                path = dargs['pic_path']
                if path == '':
                    fname = ptype
                elif not os.path.exists(path):
                    os.makedirs(path)
                    fname = os.path.join(path, ptype)
                else:
                    fname = os.path.join(path, ptype)
                print(f'Ich speichere im Pfad {fname}')
            else:
                print(f'Ich speichere im Programmordner.')
                fname = ptype
            plt.savefig(fname, dpi=600)
        else:
            return
        
    if ptype == 'original':
        _, ax = plt.subplots()
        ax.plot(x, y, label=y.name, alpha=0.5, linestyle='-', linewidth=1)
        ax.set_title('Originaldaten')    
        ax.set_xlabel('Zeit [s]')
        ax.set_ylabel('Fx [N]')

        save_func(x, ptype, kwargs)

        plt.show()

    elif ptype == 'minima':
        if 'min_count' in kwargs.keys():
            pcount = kwargs['min_count']
            if pcount < 1:
                print('Zu wenig Intervalle. Es wird kein Intervall ausgegeben. ')
                return
        else: 
            pcount = 1
        
        if 'min_rand' in kwargs.keys():
            rand_min =  kwargs['min_rand']
        else:
            rand_min = False

        if ('min_pos' in kwargs.keys()) and (rand_min == False):
            min_pos = kwargs['min_pos']
            if len(kwargs['min_pos']) != pcount:
                print("Anzahl der Positionen und Intervalle stimmt nicht überein. Keine Ausgabe.")
                return
        elif rand_min:
            min_pos = [round(random.uniform(0.01, 99.99), 2) for i in range(pcount)]
        elif ('min_pos' not in kwargs.keys()) and (rand_min == False):
            min_pos = [round(random.uniform(0.01, 99.99), 2) for i in range(pcount)]
        else:
            # Die Position an der das Intervall ausgegeben wird, wird in Prozent der Daten übergeben. 
            # Standardmäßig wird bei 1, 25, 50, 75 und 98% der Messwerte eine Ausgabe erzeugt. 
            min_pos = [0.1, 25, 50, 75, 99.9]
        
        pos_idx = [int(i/100*len(x2.index)) for i in min_pos]
        start_pos = [x2.index[i] for i in pos_idx]
        
        anz_minima = 10
        end_pos = [x2.index[i + anz_minima] for i in pos_idx]

        for start, end in zip(start_pos, end_pos):
            _, ax = plt.subplots()
            x1 = x.loc[start:end]
            y1 = y.loc[start:end]
            x3 = x2.loc[start:end]
            y3 = y2.loc[start:end]
            ax.plot(x1, y1,'k-', label=y.name, alpha=0.5, linewidth=1)
            ax.scatter(x3, y3, s=10, c='r', label='Minima')
            ax.set_title('Minima')
            ax.set_xlabel('Zeit [s]')
            ax.set_ylabel('Fx [N]')

            ax.legend(loc='center right')

            save_func(x, ptype, kwargs)

            plt.show()
    
    elif ptype == 'abstaende':
        _, axs = plt.subplots(2,1)

        axs[0].scatter(x, y, label='Abstände', s=5, c='r')
        axs[0].set_title('Abstände der Minima')
        

        if 'Median' in kwargs.keys():
            axs[0].hlines(kwargs['Median'], 0, 1, transform=axs[0].get_yaxis_transform(), colors='k', linewidth=1)
        else:
            axs[0].hlines(0, 0, 1, transform=axs[0].get_yaxis_transform(), colors='k', linewidth=1)

        if 'thresh' in kwargs.keys():
            idx = kwargs['thresh']
            axs[0].vlines(x[idx], 0, 1, transform=axs[0].get_xaxis_transform(), colors='k', linestyle='--', linewidth=1, label='Grenzwert')
            # Diagrammeinstellungen
            axs[0].set_xlim(0, x[idx+2])
            
        axs[0].set_ylim(y.min()*1.05, y.max()*1.05)
        axs[0].legend(loc='upper right')

        axs[1].plot(x2, y2, label='Originaldaten', alpha=0.5, color='r', linestyle='-', linewidth=1)
        axs[1].set_title('Originaldaten')

        if 'cut_pos' in kwargs.keys():
            axs[1].vlines(kwargs['cut_pos'], 0, 1, transform=axs[1].get_xaxis_transform(), colors='k', linestyle='--', linewidth=1, label='Grenzwert')
            axs[1].set_xlim(0, kwargs['cut_pos']*1.15)
        axs[1].set_ylim(boundaries[1])
        plt.subplots_adjust(left=0.05, right=0.98, bottom=0.05, top=0.95, hspace=0.3)

        axs[1].legend(loc='upper left')

        save_func(x, ptype, kwargs)

        plt.show()

    elif ptype == 'patches':
        if 'pcount' in kwargs.keys():
            pcount = kwargs['pcount']
            if pcount < 1:
                print('Zu wenig Intervalle. Es wird kein Intervall ausgegeben. ')
                return
        else: 
            pcount = 1
        
        if 'shift' in kwargs.keys():
            shift = kwargs['shift']
        else: 
            shift = 0

        if 'rand_patch' in kwargs.keys():
            rand_patch =  kwargs['rand_patch']
        else:
            rand_patch = False

        if ('patch_pos' in kwargs.keys()) and (rand_patch == False):
            p_pos = kwargs['patch_pos']
            if len(kwargs['patch_pos']) != pcount:
                print("Anzahl der Positionen und Intervalle stimmt nicht überein. Keine Ausgabe.")
                return
        elif rand_patch:
            p_pos = [round(random.uniform(0.01, 99.99), 2) for i in range(pcount)]
        elif ('patch_pos' not in kwargs.keys()) and (rand_patch == False):
            p_pos = [round(random.uniform(0.01, 99.99), 2) for i in range(pcount)]
        else:
            # Die Position an der das INtervall ausgegeben wird, wird in Prozent der Daten übergeben. 
            # Standardmäßig wird bei 1, 25, 50, 75 und 98% der Messwerte eine Ausgabe erzeugt. 
            p_pos = [0.1, 25, 50, 75, 99.9]
        
        pos_idx = [int(i/100*len(x2.index)) for i in p_pos]
        start_pos = [x2.index[i] for i in pos_idx]
        end_pos = [x2.index[i+1] for i in pos_idx]

        for start, end in zip(start_pos, end_pos):
            _, ax = plt.subplots()
            x1 = x.loc[start:end]
            y1 = y.loc[start:end]
            x3 = [x2[start], x2[end]]
            y3 = [y2[start], y2[end]]
            ax.plot(x1, y1,'k-', label=y.name, alpha=0.5, linewidth=1)
            ax.scatter(x3, y3, s=10, c='r', label='Minima')

            start_idx = start + shift
            end_idx = end - shift

            y_pos = y.loc[start_idx:end_idx].min()
            height = (y.loc[start_idx:end_idx].max() - y_pos)*1.1

            x_pos = x.loc[start_idx]
            width = x.loc[end_idx] - x.loc[start_idx]      

            # Füge eine horizontale Linie bei 
            ax.hlines(y.loc[start_idx:end_idx].mean(),x3[0], x3[1], colors='r', linewidth=1, label='Median', linestyle='--')

            face = Rectangle((x_pos, y_pos), width, height, facecolor="green", alpha=0.1)
            edge = Rectangle((x_pos, y_pos), width, height, edgecolor='green', linewidth=0.5, fill=False)

            ax.add_patch(face)
            ax.add_patch(edge)

            ax.set_xlabel('Zeit [s]')
            ax.set_ylabel('Fx [N]')

            plt.legend()

            save_func(x, ptype, kwargs)

            plt.show()
            
    elif ptype == 'filtered':
        _, ax= plt.subplots()
        ax.plot(x, y,'k-', label='Rohdaten',  alpha=0.5, linewidth=1)

        if 'filter' in kwargs.keys():
            filt = kwargs['filter']
            ax.plot(x2, y2,'b-',linewidth=0.5, label=f'{filt}')
        
        if 'rkf' in kwargs.keys():
            rkf = kwargs['rkf']
            ax.hlines(rkf,0, 1, transform=ax.get_yaxis_transform(), colors='r', linewidth=1, label='Median', linestyle='--')
            ax.text(0.98, 0.98, f'COF = {round(rkf, 2)}', color='r', horizontalalignment='right', verticalalignment='top', transform=ax.transAxes)

        if y.name == 'COF':
            ax.set_ylabel('COF [-]')
        else:
            ax.set_ylabel(f'{y.name}')
        if x.name == 'Time':
            ax.set_xlabel('Zeit [s]')
        if x.name == 'V_weg':
            ax.set_xlabel('Verschleißweg [m]')

        ax.legend(loc='upper left')

        save_func(x, ptype, kwargs)

        plt.show()
 
    elif ptype == 'export':
        _, axs = plt.subplots(2,1, sharex=True, sharey=True)

        axs[0].plot(x, y, 'b-', lw=1, label='Originaldaten')
        axs[1].plot(x2, y2, 'r-', lw=1, label='Reduzierte Daten')
        
        # Das könnte man noch schöner machen
        axs[0].set_ylabel(y.name)
        axs[1].set_ylabel(y.name)

        axs[1].set_xlabel(x.name)
        axs[0].legend(loc='lower right')
        axs[1].legend(loc='lower right')

        plt.show()

    return

def reduce_data(dat, n=500, p=3):
    return sf(dat, n, p)    # (Daten, Glättungsbereich, Polynom n-ten Grades)

def gleit_durch(x, N=500):
    return x.rolling(window=N).mean().iloc[N-1:].values

def median_filt(x, n=500):
    return medfilt(x, n)

def low_pass(dat, fo=2, fco=10, sf=500):
    '''
        fo: filter_order
        fco: frequency_cutoff
        sf: sampling_frequency
    '''

    # Create the filter
    b, a = butter(fo, fco, btype='low', output='ba', fs=sf)

    # Apply the filter
    filtered = filtfilt(b, a, dat)
    return filtered

def high_pass(dat, fo=2, fco=10, sf=500):
    '''
        fo: filter_order
        fco: frequency_cutoff
        sf: sampling_frequency
    '''
    
    # Create the filter
    b, a = butter(fo, fco, btype='high', output='ba', fs=sf)

    # Apply the filter
    filtered = filtfilt(b, a, dat)
    return filtered

def find_minima(x, dist=10, h = -2):
    '''
        Die find_peaks Funktion sucht nach lokalen Maxima
        der _height_-Parameter wird genutzt, um alle auftretenden Peaks unterhalt eines Schwellwertes zu ignorieren
        durch die Multiplikation mit -1 werden Minima gefunden.
        Die Schwelle von -2 ist willkürlich gewählt und muss validiert werden
        TODO: Schwellwert überprüfen
    '''
    peaks, _ = find_peaks(x*(-1),distance=dist, height = h)
    return peaks

def test_minima(df, minima, pos=None, rand=False, anz=1, save=False, p_path=None):
    plot_data(df['Time'], df['Fx'], minima['Time'], minima['Fx'], ptype='minima', min_rand=rand, min_count=anz, min_pos=pos, save=save, pic_path=p_path)

def find_einlauf(minima, gw=0.05, off=1):
    # zeige die Abstände zwischen den Minima an
    dist = np.diff(minima['Time'].values)
    # setze Abstände in Relation zu Median
    dist -= np.median(dist)

    # Finde ersten Punkt, der sich in einem Streuband 5% um den Median befindet
    thresh_ind = np.argmax((dist > -gw) & (dist < gw))

    # Position in Originaldaten
    cut = minima['Time'].iloc[thresh_ind + off]
    return dist, thresh_ind, cut

def test_einlauf(df, dist, minima, thresh_ind, off, cut, save, p_path):
    x_bound_cut = minima['Time'].iloc[thresh_ind+8]
    plot_data(range(len(dist)), dist, df['Time'], df['Fx'], offset=off, cut_pos=cut, ptype='abstaende', thresh=thresh_ind, boundaries=[[0, x_bound_cut], [0, df['Fx'].max()]], save=save, pic_path=p_path)      

def test_area(df_2, minima_2, patch_pos=[0.1, 25, 50, 75, 99.9], pcount=5, shift=0, rand_patch=False, save=False, p_path=None):
    plot_data(df_2['Time'], df_2['Fx'],minima_2['Time'], minima_2['Fx'], ptype='patches', patch_pos=patch_pos, pcount=pcount, shift=shift, rand_patch=rand_patch, save=save, pic_path=p_path)

def save_as_xls(s, path=''):
    if path == '':
        # nehme aktuelles Ausführungsverezichnis
        fname = 'umt-export'
        path = fname + '.xlsx'
    else:
        fname = os.path.split(path)[1].split('.')[1]

    s.to_excel(path, sheet_name=fname)
    


def main():
    # fname = 'data/txt-data.txt'
    fname = 'data/Var-s/EB4_50N_5mmHub_1.5Hz_450m_DAF_1mm_01_WC-Co(DFH).txt'
    df = get_data(fname)

    if df is not None: 
        pass
    else:
        return

    # Daten anschauen
    # plot_data(df['Time'], df['Fx'])

    # Bilde Absolutwerte von x
    df['Fx'] = df['Fx'].abs()

    # series = ['Fx']
    loc_minima = find_minima(df['Fx'].values)
    minima = df.iloc[loc_minima]

    # teste die Positionen der Minima
    # test_minima(df, minima, rand=True, anz=3)

    dist, thresh_ind, cut = find_einlauf(minima)

    # teste Position des Thresholds + Zeichne Threshold in Originaldaten
    # test_einlauf(df, dist, minima, thresh_ind, cut)
        
    # Schneide Anfangsbereich ab und kürze Minima entsprechend
    '''TODO: Sollte man jetzt den 8. Abstand nehmen, oder lieber 2-3 Minima weiter in die Daten gehen?

    '''
    df_2 = df[df.Time >= cut]
    minima_2 = minima[:].iloc[thresh_ind+1:]


    # Slice den Dataframe an den Stellen um die Minima
    to_cut = minima_2.index
    shift = 5

    # Teste, ob Versatz korrekt eingestellt ist
    test_area(df_2, minima_2, patch_pos=[0.1, 25, 50, 75, 99.9], shift=shift, rand_patch=False)
    

    # Erstelle Liste mit Indices aller gewünschter Werte
    liste2 = []
    for j in range(len(to_cut)-1):
        liste2 += [i for i in range(to_cut[j]+shift, to_cut[j+1]-shift)]

    # Bereinigte Daten von Fx
    df_3 = df_2[df_2.index.isin(liste2)]

    # plot_data(df_3['Time'], df_3['Fx'], ptype='filtered', filter='savgol')
    
    # Berechnung des Reibungskoeffizienten
    df_3['RKF'] = df_3['Fx']/df_3['Fz']
    
    # Plotte den Reibkoeffizienten
    # plot_data(df_3['Time'], df_3['RKF'], ptype='filtered', filter='savgol')

    # Berechnung des Verschleißwegs
    hub = 8         # [mm]
    freq = 1.5      # [Hz]

    df_3['V_weg'] = (hub * freq * df_3['Time'] *2) / 1000

    # plot_data(df_3['V_weg'], df_3['RKF'], ptype='filtered', filter='rolling')

    # Berechnung Reibungskoeffizient
    x_start = 112
    x_end = df_3['V_weg'].index[-1]

    idx_rkf_strt = df_3['V_weg'].loc[df_3['V_weg'] < x_start].index[-1]
    idx_rkf_end = x_end



    # plotte die Originaldaten und die gefilterten Daten
    # add_data(df, series, 'savgol')
    rkf_stat = df_3['RKF'].iloc[idx_rkf_strt:idx_rkf_end].mean()

    # plot_data(df_3['V_weg'], df_3['RKF'], ptype='filtered', filter='rolling', rkf=rkf_stat)
    
    n_red = 10
    # plot_data(df_3['V_weg'][::n_red], df_3['RKF'][::n_red], ptype='filtered', filter='savgol', rkf=rkf_stat)

if __name__ == '__main__':
    main()



