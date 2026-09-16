-- =============================================================================
-- DISPARO DIÁRIO DO CARROSSEL PELO SUPABASE (substitui o n8n)
--
-- Todo dia às 06:00 de Brasília (09:00 UTC) o Supabase chama a API de
-- repository_dispatch do GitHub, que roda "Publicar treino do dia" na hora.
-- Disparo por API não passa pela fila do `schedule` do GitHub, que atrasa horas.
-- Os horários do `schedule` no workflow continuam como rede de segurança.
--
-- ANTES DE RODAR: troque COLE_AQUI_O_TOKEN_DO_GITHUB pelo token (fine-grained)
-- com acesso só ao natacao-treinos e permissão Contents: Read and write.
-- O token fica no Vault do Supabase, criptografado; não vai para o código.
--
-- Pode rodar de novo quando trocar o token: ele atualiza o segredo e o agendamento.
-- =============================================================================

create extension if not exists pg_cron;
create extension if not exists pg_net;

-- 1. Token do GitHub no Vault (cria ou atualiza)
do $token$
declare
    novo text := 'COLE_AQUI_O_TOKEN_DO_GITHUB';
    existente uuid;
begin
    if novo like 'COLE_AQUI%' then
        raise exception 'Cole o token do GitHub no lugar de COLE_AQUI_O_TOKEN_DO_GITHUB antes de rodar.';
    end if;
    select id into existente from vault.secrets where name = 'github_token_natacao_treinos';
    if existente is null then
        perform vault.create_secret(novo, 'github_token_natacao_treinos', 'Dispara a publicação diária do carrossel no GitHub Actions');
    else
        perform vault.update_secret(existente, novo);
    end if;
end
$token$;

-- 2. A chamada ao GitHub, numa função (o agendamento e o teste usam a mesma)
create or replace function public.disparar_carrossel_do_dia()
returns bigint
language sql
security definer
set search_path = public, extensions
as $$
    select net.http_post(
        url := 'https://api.github.com/repos/Nicevargas/natacao-treinos/dispatches',
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || (select decrypted_secret from vault.decrypted_secrets where name = 'github_token_natacao_treinos'),
            'Accept', 'application/vnd.github+json',
            'X-GitHub-Api-Version', '2022-11-28',
            'User-Agent', 'supabase-natacao-criativa',
            'Content-Type', 'application/json'
        ),
        body := jsonb_build_object('event_type', 'publicar-treino')
    );
$$;

-- Só o próprio banco chama: nada de expor pela API do app.
revoke all on function public.disparar_carrossel_do_dia() from public, anon, authenticated;

-- 3. Agendamento: 09:00 UTC = 06:00 em Brasília (sem horário de verão)
select cron.unschedule(jobid) from cron.job where jobname = 'publicar-carrossel-6h';
select cron.schedule('publicar-carrossel-6h', '0 9 * * *', 'select public.disparar_carrossel_do_dia()');

-- 4. Conferência: deve aparecer uma linha, ativa, "0 9 * * *"
select jobname, schedule, active from cron.job where jobname = 'publicar-carrossel-6h';
