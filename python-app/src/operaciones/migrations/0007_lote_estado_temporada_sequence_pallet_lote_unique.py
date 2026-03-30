"""
Migration 0007: Agrega estado, temporada_codigo, correlativo_temporada al Lote,
crea SequenceCounter, y agrega restriccion de unicidad de lote en PalletLote.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0006_align_field_details'),
    ]

    operations = [
        # 1. Agregar campo estado al Lote
        migrations.AddField(
            model_name='lote',
            name='estado',
            field=models.CharField(
                choices=[
                    ('abierto',    'Abierto'),
                    ('en_proceso', 'En proceso'),
                    ('cerrado',    'Cerrado'),
                    ('finalizado', 'Finalizado'),
                    ('anulado',    'Anulado'),
                ],
                default='abierto',
                max_length=20,
                db_index=True,
                help_text='Estado del lote planta (abierto → en_proceso → cerrado → finalizado/anulado)',
            ),
        ),

        # 2. Agregar campo temporada_codigo al Lote
        migrations.AddField(
            model_name='lote',
            name='temporada_codigo',
            field=models.CharField(
                blank=True,
                default='',
                max_length=20,
                db_index=True,
                help_text='Codigo de temporada operativa. Ej: 2025-2026.',
            ),
        ),

        # 3. Agregar campo correlativo_temporada al Lote
        migrations.AddField(
            model_name='lote',
            name='correlativo_temporada',
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                help_text='Correlativo ascendente dentro de la temporada. No se reutiliza si el lote es anulado.',
            ),
        ),

        # 4. Crear tabla SequenceCounter
        migrations.CreateModel(
            name='SequenceCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entity_name', models.CharField(max_length=50, db_index=True)),
                ('dimension',   models.CharField(max_length=50, db_index=True)),
                ('last_value',  models.PositiveIntegerField(default=0)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'operaciones_sequence_counter',
            },
        ),
        migrations.AddConstraint(
            model_name='sequencecounter',
            constraint=models.UniqueConstraint(
                fields=['entity_name', 'dimension'],
                name='uq_seq_entity_dimension',
            ),
        ),
        migrations.AddIndex(
            model_name='sequencecounter',
            index=models.Index(
                fields=['entity_name', 'dimension'],
                name='ix_seq_entity_dim',
            ),
        ),

        # 5. Agregar restriccion de unicidad de lote en PalletLote
        #    (un lote solo puede pertenecer a un pallet)
        migrations.AddConstraint(
            model_name='palletlote',
            constraint=models.UniqueConstraint(
                fields=['lote'],
                name='uq_pallet_lote_lote_unico',
            ),
        ),
    ]
