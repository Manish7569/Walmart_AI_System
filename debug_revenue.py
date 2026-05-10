#!/usr/bin/env python3
import os
os.environ['WALMART_AI_FAST_STARTUP'] = '1'

from data.generators.engine import engine
engine.initialize(verbose=True, fast=True)

pos = engine.pos
print(f'\nPOS shape: {pos.shape}')
print(f'POS columns: {list(pos.columns)}')
print(f'Has total_revenue: {"total_revenue" in pos.columns}')
print(f'Has date: {"date" in pos.columns}')
print(f'Has department: {"department" in pos.columns}')

if 'total_revenue' in pos.columns:
    print(f'Total revenue sum: ${pos["total_revenue"].sum():,.2f}')
    print(f'Revenue rows count: {len(pos)}')
    print(f'\nFirst 5 rows:')
    print(pos[['date', 'department', 'total_revenue']].head())
