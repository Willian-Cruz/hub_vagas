{{
  config(
    severity = 'warn',
    meta = {
      'documentacao': 'Verifica que há vagas com tecnologias detectadas no mart_vagas. '
                      'Se 0 vagas tiverem tecnologias, o regex da seed não está funcionando.'
    }
  )
}}

select count(*) as vagas_sem_tecnologia
from {{ ref('mart_vagas') }}
where tecnologias is null or tecnologias = ''
