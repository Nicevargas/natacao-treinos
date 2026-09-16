-- =============================================================================
-- TESTE DO DISPARO (rode depois do disparo-diario.sql)
--
-- Passo 1: rode só a linha abaixo. Ela chama o GitHub agora. Se o carrossel do
-- dia já foi publicado, o workflow roda e sai sem postar de novo.
-- =============================================================================
select public.disparar_carrossel_do_dia();

-- Passo 2: espere uns 5 segundos e rode esta consulta.
-- status_code 204 = GitHub aceitou. 401 = token errado ou sem permissão.
select id, status_code, left(content, 200) as resposta, created
from net._http_response
order by created desc
limit 3;
