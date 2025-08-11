import pandas as pd
from collections import deque
import matplotlib.pyplot as plt
import textwrap

BITPANDA_CSV_DATEI = "upload/bitpanda-trades.csv"
ZIELJAHR = 2025 # <-- Ändern Sie hier das gewünschte Steuerjahr
    
DEIN_NAME = "Max Mustermann"
DEINE_STRASSE = "Musterstraße 1"
DEINE_STADT_PLZ = "12345 Musterstadt"

# ############################################################################
# FUNKTION 1: Berechnet die Gewinne/Verluste für alle Jahre
# ############################################################################
def calculate_crypto_gains_by_year(file_path):
    """
    Lädt eine Bitpanda-CSV-Datei, berechnet die Kapitalgewinne nach der FIFO-Methode
    und erstellt eine detaillierte Master-CSV-Datei für alle Jahre.
    """
    try:
        df = pd.read_csv(file_path, skiprows=6)
        df.columns = df.columns.str.strip()
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True)
        df.sort_values(by='Timestamp', inplace=True)
        df.reset_index(drop=True, inplace=True)
        numeric_cols = ['Amount Fiat', 'Amount Asset']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        purchase_queues = {}
        sales_records = []
        crypto_transactions = df[df['Asset class'] == 'Cryptocurrency'].copy()

        for index, row in crypto_transactions.iterrows():
            asset = row['Asset']
            timestamp = row['Timestamp']
            transaction_type = row['Transaction Type']
            amount_asset = row['Amount Asset']
            amount_fiat = abs(row['Amount Fiat'])
            
            if asset not in purchase_queues:
                purchase_queues[asset] = deque()

            if transaction_type == 'buy' or (transaction_type == 'trade' and row['In/Out'] == 'incoming'):
                cost_per_unit = amount_fiat / amount_asset if amount_asset > 0 else 0
                purchase_queues[asset].append({
                    'timestamp': timestamp, 'quantity': amount_asset, 'cost_per_unit': cost_per_unit
                })
            elif transaction_type == 'sell' or (transaction_type == 'trade' and row['In/Out'] == 'outgoing'):
                proceeds, sold_quantity, cost_basis = amount_fiat, amount_asset, 0
                temp_sold_quantity = sold_quantity
                first_purchase_date = timestamp
                purchase_dates_for_sale = []

                while temp_sold_quantity > 0 and purchase_queues.get(asset):
                    oldest_purchase = purchase_queues[asset][0]
                    quantity_to_sell = min(temp_sold_quantity, oldest_purchase['quantity'])
                    
                    cost_basis += quantity_to_sell * oldest_purchase['cost_per_unit']
                    purchase_dates_for_sale.append(oldest_purchase['timestamp'])
                    
                    temp_sold_quantity -= quantity_to_sell
                    oldest_purchase['quantity'] -= quantity_to_sell
                    if oldest_purchase['quantity'] < 1e-9:
                        purchase_queues[asset].popleft()
                
                if purchase_dates_for_sale:
                    first_purchase_date = purchase_dates_for_sale[0]

                sales_records.append({
                    'sale_date': timestamp, 'gain_loss_eur': proceeds - cost_basis, 'holding_period_days': (timestamp - first_purchase_date).days
                })

        gains_df = pd.DataFrame(sales_records)
        gains_df['gain_loss_eur'] = gains_df['gain_loss_eur'].round(2)  # Rundung auf 2 Nachkommastellen
        gains_df['taxable'] = gains_df['holding_period_days'] <= 365
        gains_df['sale_year'] = gains_df['sale_date'].dt.year

        # Ensure datetimes are timezone unaware before writing to Excel
        if pd.api.types.is_datetime64_any_dtype(gains_df['sale_date']):
            gains_df['sale_date'] = gains_df['sale_date'].dt.tz_localize(None)

        gains_df.to_excel('output/steuerreport_kryptogewinne_details.xlsx', index=False)
        print("Master-Datei 'output/steuerreport_kryptogewinne_details.xlsx' wurde erfolgreich erstellt.")
        return True
    except FileNotFoundError:
        print(f"FEHLER: Die Datei '{file_path}' wurde nicht gefunden. Bitte stellen Sie sicher, dass sie im selben Ordner wie das Skript liegt.")
        return False
    except Exception as e:
        print(f"Ein Fehler bei der Hauptberechnung ist aufgetreten: {e}")
        return False

# ############################################################################
# FUNKTION 2: Erstellt die finalen Dokumente für ein bestimmtes Jahr
# ############################################################################
def create_final_documents_for_year(year, full_details_xlsx, user_name, street, city_zip):
    """
    Filtert die Steuerdaten für ein bestimmtes Jahr und erstellt ein PDF
    sowie eine detaillierte XLSX-Datei für dieses Jahr.
    """
    try:
        df_full = pd.read_excel(full_details_xlsx)
        df_year = df_full[df_full['sale_year'] == year].copy()

        if df_year.empty:
            print(f"Keine Daten für das Jahr {year} gefunden.")
            return

        # Ensure datetimes are timezone unaware before writing to Excel
        if pd.api.types.is_datetime64_any_dtype(df_year['sale_date']):
            df_year['sale_date'] = pd.to_datetime(df_year['sale_date']).dt.tz_localize(None)

        # Detaillierte XLSX für das spezifische Jahr erstellen
        df_year_final_xlsx = df_year.rename(columns={
            'sale_date': 'Verkaufsdatum', 'gain_loss_eur': 'Gewinn/Verlust (EUR)', 'holding_period_days': 'Haltedauer (Tage)'
        })[['Verkaufsdatum', 'Gewinn/Verlust (EUR)', 'Haltedauer (Tage)']]
        df_year_final_xlsx['Gewinn/Verlust (EUR)'] = df_year_final_xlsx['Gewinn/Verlust (EUR)'].round(2)  # Rundung auf 2 Nachkommastellen
        output_xlsx_year_details = f'output/Steuerreport_{year}_Detailnachweis.xlsx'
        df_year_final_xlsx.to_excel(output_xlsx_year_details, index=False)
        print(f"Detaillierter XLSX-Report für {year} wurde erstellt: '{output_xlsx_year_details}'")

        taxable_result = df_year[df_year['taxable']]['gain_loss_eur'].sum().round(2)  # Rundung auf 2 Nachkommastellen
        is_loss = taxable_result < 0
        
        # Visuell ansprechendes PDF erstellen
        output_pdf_year = f'output/Steuererklaerung_{year}_Final.pdf'
        colors = {"primary": "#1D3557", "secondary": "#457B9D", "background": "#F1FAEE", "text": "#212529"}
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.patch.set_facecolor('w')
        ax = fig.add_axes([0, 0, 1, 1])
        ax.axis('off')

        ax.axhline(y=0.95, xmin=0.08, xmax=0.92, color=colors['secondary'], linewidth=1.5)
        ax.text(0.5, 0.91, f"Zusammenfassung für die Anlage SO – Steuerjahr {year}", ha='center', va='center', fontsize=18, weight='bold', color=colors['primary'])
        ax.text(0.5, 0.88, "Private Veräußerungsgeschäfte mit Kryptowährungen", ha='center', va='center', fontsize=11, color=colors['text'])
        ax.axhline(y=0.86, xmin=0.08, xmax=0.92, color=colors['secondary'], linewidth=1.5)

        ax.text(0.1, 0.82, user_name, fontsize=10, color=colors['text'])
        ax.text(0.1, 0.80, street, fontsize=10, color=colors['text'])
        ax.text(0.1, 0.78, city_zip, fontsize=10, color=colors['text'])

        intro_text = f"Sehr geehrte Damen und Herren,\n\nanbei die Zusammenfassung meiner steuerpflichtigen Ergebnisse für das Steuerjahr {year}. Die Berechnung erfolgte nach der FIFO-Methode."
        ax.text(0.1, 0.68, textwrap.fill(intro_text, 90), fontsize=10, va='top', linespacing=1.5)

        result_title = f"Steuerpflichtiger Gesamtverlust {year}" if is_loss else f"Steuerpflichtiger Gesamtgewinn {year}"
        result_value = f"{taxable_result:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".")
        ax.text(0.5, 0.52, result_title, fontsize=11, ha='center', color=colors['text'])
        ax.text(0.5, 0.46, result_value, fontsize=22, weight='bold', ha='center', color=colors['primary'], bbox=dict(boxstyle="round,pad=0.6", fc='#F0F8FF', ec=colors['secondary']))

        note_text = "Dieser Verlust kann in der Anlage SO geltend gemacht werden." if is_loss else "Dieser Gewinn ist in der Anlage SO anzugeben."
        ax.text(0.5, 0.38, textwrap.fill(note_text, 85), ha='center', va='top', fontsize=9, style='italic', color=colors['text'])

        proof_text = f"Ein detaillierter Nachweis befindet sich im Dokument: '{output_xlsx_year_details}'"
        ax.text(0.5, 0.25, textwrap.fill(proof_text, 85), ha='center', va='top', fontsize=9, bbox=dict(boxstyle="round,pad=0.4", fc=colors['background'], ec=colors['secondary'], ls='--'))
        
        plt.savefig(output_pdf_year, format='pdf')
        print(f"Finales PDF für {year} wurde erstellt: '{output_pdf_year}'")
    except FileNotFoundError:
        print(f"FEHLER: Die Quelldatei '{full_details_xlsx}' wurde nicht gefunden.")
    except Exception as e:
        print(f"Ein Fehler bei der PDF-Erstellung ist aufgetreten: {e}")


# ############################################################################
# HAUPTAUSFÜHRUNG: Hier starten Sie das Skript
# ############################################################################
if __name__ == "__main__":
    BITPANDA_CSV_DATEI = BITPANDA_CSV_DATEI
    ZIELJAHR = ZIELJAHR 
    
    DEIN_NAME = DEIN_NAME
    DEINE_STRASSE = DEINE_STRASSE
    DEINE_STADT_PLZ = DEINE_STADT_PLZ
    # --------------------
    print("Führe Hauptberechnung durch...")
    success = calculate_crypto_gains_by_year(BITPANDA_CSV_DATEI)
    
    if success:
        print(f"\nErstelle nun die Dokumente für das Jahr {ZIELJAHR}...")
        create_final_documents_for_year(
            year=ZIELJAHR,
            full_details_xlsx='output/steuerreport_kryptogewinne_details.xlsx',
            user_name=DEIN_NAME,
            street=DEINE_STRASSE,
            city_zip=DEINE_STADT_PLZ
        )
    print("\nSkript beendet.")