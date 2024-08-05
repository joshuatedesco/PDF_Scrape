from os import path
import os
import fitz
import re
import pandas as pd

# Example weight rules
weights = {
    'Tee': {'S': 5.0, 'M': 5.9, 'L': 6.3, 'XL': 7.4, '2XL': 8.2, '3XL': 9.0, '4XL': 9.8},
    'Sweatshirt': {'S': 11.7, 'M': 12.6, 'L': 14.1, 'XL': 16.3, '2XL': 17.9, '3XL': 19.4, '4XL': 20.9},
    'Hoodie': {'S': 15.5, 'M': 17.0, 'L': 19.5, 'XL': 21, '2XL': 22.5, '3XL': 24, '4XL': 25.5},
    'Sweatpants': {'S': 11.7, 'M': 12.6, 'L': 14.1, 'XL': 16.3, '2XL': 17.9, '3XL': 19.4, '4XL': 20.9},
    'Shorts': {'S': 5.0, 'M': 5.9, 'L': 6.3, 'XL': 7.4, '2XL': 8.2, '3XL': 9.0, '4XL': 9.8}
    # Add more types and sizes as needed
}

fixed_donations = {
    'Tee': 5.8,  # Donation for each Tee
    'Sweatshirt': 7.55,  # Donation for each Sweatshirt
    'Hoodie': 10.5,  # Donation for each Hoodie
    'Sweatpants': 10.5,  # Donation for each Sweatpants
    'Shorts': 5,  # Donation for each Shorts
}

size_order = ['XS','S', 'M', 'L', 'XL', '2XL', '3XL', '4XL','5XL']

def get_item_weight(item_type, item_size):
    return weights.get(item_type, {}).get(item_size, 0)  # Returns 0 if type/size not found
    
def split_info(order_info: str):
    order_num = re.search(r'Order #(\w+)', order_info)[1]
    order_details, item_info = re.split(r'Order #\w+', order_info, maxsplit=1)
    order_details = re.split(r'\n\w{3} \d{1,2}, \d{4}, \d{2}:\d{2} \w{2}\n', order_details, maxsplit=1)[1]

    return order_num, item_info, order_details


def get_cost(item):
    if 'Tee' in item:
        return 14.2
    if 'Sweatshirt' in item:
        return 22.45
    if 'Hoodie' in item:
        return 29.5
    if 'Sweatpants' in item:
        return 29.5
    if 'Shorts' in item:
        return 19.5


def get_buyer_data(order_details: str):
    buyer_info = {}
    order_details = re.split(r'\nBuyer\n', order_details, maxsplit=1)[-1].strip()
    buyer_info['name'] = re.match(r'([^\n]+)\n', order_details)[1]
    order_details = re.split(buyer_info['name'], order_details)[-1].strip()
    buyer_info['street'] = re.match(r'([^\n]+)\n', order_details)[1]

    addr_pattern = r'([\w ]+),([a-zA-Z\s]+)\n*([\d\n-]{4,})\nUnited States'
    address = re.search(addr_pattern, order_details)
    buyer_info['city'] = address[1].strip()
    buyer_info['state'] = address[2].strip()
    buyer_info['zipcode'] = str(address[3])#.zfill(7)

    email_pattern = r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7})\b'
    try:
        buyer_info['email'] = re.search(email_pattern, order_details)[1]
    except TypeError:
        order_details = re.sub(r'\n(\w+\.com\n)', r'\1', order_details)
        order_details = re.sub(r'\n([com]+\n)', r'\1', order_details)
        buyer_info['email'] = re.search(email_pattern, order_details)[1]
    buyer_info['phone'] = re.search(r'\+\d \d{3}-\d{3}-\d{4}', order_details)[0]

    return buyer_info


def get_order_data(order_info):
    order_num, item_info, order_details = split_info(order_info)
    buyer_info = get_buyer_data(order_details)
    item_info = item_info.split('Items')[0].strip()
    items = re.split(r'(\$\d+\.\d+)', item_info)
    order_list = []

    for item, price in zip(items[0:-1:2], items[1:-1:2]):
        order_data = {}
        order_data['order_number'] = order_num
        
        order_data['Item'] = re.match(r'\n*([^\n]+)\n', item)[1]
        order_data['total'] = float(price.split('$')[1])
        order_data['quantity'] = int(re.search(r'\n(\d+)\n', item)[1])
        order_data['Cost'] = get_cost(order_data['Item'])
        order_data['options'] = re.search(r'\n(Size: \w+\nColor:[\w\(\)\~ ]+)\n', item)[1]
        order_data['size'] = re.search(r'Size: (\w+)\n', order_data['options'])[1]
        order_data['color'] = re.search(r'Color: ([\w\(\)\~ ]+)', order_data['options'])[1]
        item_type = 'Tee' if 'Tee' in order_data['Item'] else \
            'Sweatshirt' if 'Sweatshirt' in order_data['Item'] else \
            'Hoodie' if 'Hoodie' in order_data['Item'] else \
            'Sweatpants' if 'Sweatpants' in order_data['Item'] else \
            'Shorts' if 'Shorts' in order_data['Item'] else 'Other'
        item_size = re.search(r'Size: (\w+)\n', order_data['options'])[1]
        item_size = item_size.upper()
        order_data['Weight'] = get_item_weight(item_type, item_size) #added code #josh
        order_data['Total Weight'] = order_data['Weight'] * order_data['quantity']
        order_data['Donation_Sub'] = fixed_donations.get(item_type, 0)
        order_data['Donation Total'] = order_data['Donation_Sub'] * order_data['quantity']
        order_data['Moo_Fee'] = 0.1 * order_data['Cost'] * order_data['quantity']
        order_data['email'] = buyer_info['email']
        order_data['Name'] = buyer_info['name']
        order_data['Street'] = buyer_info['street']
        order_data['City'] = buyer_info['city']
        order_data['Zipcode'] = buyer_info['zipcode']
        order_data['State'] = buyer_info['state']
        order_data['Phone'] = buyer_info['phone']

        order_list.append(order_data)

    return order_list


if __name__ == '__main__':
    if not os.path.exists("Input"):
        print('[ERROR]: Input folder missing!!')
    files = [f for f in os.listdir('Input') if f.endswith('.pdf')]
    combined_order_list = []
    
    for f_name in files:
        print(f'[Scraping...]: {f_name}', end='\t')
        file_path = path.join('Input', f_name)
        order_info = ''
        split_pattern = r'\s\d{1,3}\/\d{1,3}\s'   # pattern of page number eg 1/19
        end_sent = 'Thank you for your order!'    # last sentence of an order
        end_check = False

        with fitz.open(file_path) as doc:
            for page in doc:
                page_text = page.get_text()
                page_text = re.split(split_pattern, page_text, maxsplit=1)[-1]

                if end_check and page_text.startswith('Color:'):
                    cut_text = re.match(r'Color:[\w ~]+\n', page_text)[0]
                    page_text = re.sub(r'Color:[\w ~]+\n', '', page_text, count=1)
                    order_info = re.sub(r'\d+\n\$\d+\.\d+\n*$', rf'{cut_text}\0', order_info)
                    order_info += page_text
                elif end_check and page_text.startswith('Size:'):
                    cut_text = re.match(r'Size:[\w ]+\nColor:[\w ~]+\n', page_text)[0]
                    page_text = re.sub(r'Size:[\w ]+\nColor:[\w ~]+\n', '', page_text, count=1)
                    order_info = re.sub(r'\d+\n\$\d+\.\d+\n*$', rf'{cut_text}\0', order_info)
                    order_info += page_text
                elif end_check and page_text.startswith('SKU'):
                    cut_text = re.match(r'SKU[\w :]+\nSize:[\w ]+\nColor:[\w ~]+\n', page_text)[0]
                    page_text = re.sub(r'SKU[\w :]+\nSize:[\w ]+\nColor:[\w ~]+\n', '', page_text, count=1)
                    order_info = re.sub(r'\d+\n\$\d+\.\d+\n*$', rf'{cut_text}\0', order_info)
                    order_info += page_text
                else:
                    order_info += page_text
                
                end_check = False
                if end_sent in order_info:
                    data_list = get_order_data(order_info)
                    combined_order_list.extend(data_list)
                    order_info = ''

                elif re.search(r'\d+\n\$\d+\.\d+\n*$', order_info):
                    end_check = True
        print('[Completed]')

    df = pd.DataFrame(combined_order_list)
    summary_df1 = pd.DataFrame()
    summary_df1['Item'] = df['Item'].apply(lambda item: item.strip().split()[-1])
    summary_df1[['quantity', 'Size']] = df[['quantity', 'size']]
    colors = r'(Black|Green|Grey|Brown|White|Whtie|Back|Tan)'
    summary_df1['Color'] = df['color'].apply(lambda c: re.search(colors, c)[0])
    summary_df1['Color'] = summary_df1['Color'].replace({'Whtie': 'White', 'Back': 'Black'})
    summary_df2 = summary_df1.groupby(['Item', 'Size', 'Color']).sum()['quantity'].reset_index()
    
    # Ensure the DataFrame is sorted as needed before writing to Excel
    summary_df2['Size'] = pd.Categorical(summary_df2['Size'], categories=size_order, ordered=True)
    summary_df2 = summary_df2.sort_values(['Item', 'Color', 'Size'])

    # Then write to Excel as you already do
    output_file_path = path.join('Output', 'Order details.xlsx')
    with pd.ExcelWriter(output_file_path) as writer:
        df.to_excel(writer, sheet_name='orders', index=False)
        summary_df1.to_excel(writer, sheet_name='Production Summary', header=True, index=False)
        summary_df2.to_excel(writer, sheet_name='Production Summary', startcol=5, startrow=0, header=True, index=False)

    print(f'\nData saved in {output_file_path}\n')
    