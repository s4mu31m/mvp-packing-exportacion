from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0008_alter_lote_temporada_codigo'),
    ]

    operations = [
        # Agregar campo real horas_desverdizado al modelo Desverdizado
        migrations.AddField(
            model_name='desverdizado',
            name='horas_desverdizado',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text="Horas planificadas de desverdizado. Reemplaza el campo proceso para este dato.",
            ),
        ),
        # Nuevo modelo CalidadPalletMuestra
        migrations.CreateModel(
            name='CalidadPalletMuestra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('operator_code', models.CharField(blank=True, default='', max_length=50)),
                ('source_system', models.CharField(blank=True, default='local', max_length=20)),
                ('pallet', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='muestras_calidad',
                    to='operaciones.pallet',
                )),
                ('numero_muestra', models.PositiveSmallIntegerField(
                    default=1,
                    help_text='Numero correlativo de muestra en la sesion (1, 2, 3...)',
                )),
                ('temperatura_fruta', models.DecimalField(
                    blank=True, decimal_places=2, help_text='°C', max_digits=5, null=True,
                )),
                ('peso_caja_muestra', models.DecimalField(
                    blank=True, decimal_places=3, help_text='kg', max_digits=8, null=True,
                )),
                ('n_frutos', models.IntegerField(
                    blank=True, null=True,
                    help_text='Numero de frutos en la caja muestra',
                )),
                ('aprobado', models.BooleanField(blank=True, null=True, help_text='Muestra aprobada')),
                ('observaciones', models.TextField(blank=True, default='')),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={
                'db_table': 'operaciones_calidad_pallet_muestra',
                'ordering': ['pallet', 'numero_muestra'],
            },
        ),
    ]
