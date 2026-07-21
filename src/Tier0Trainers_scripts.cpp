#include "ScriptMgr.h"
#include "Config.h"
#include "Log.h"

class Tier0Trainers_World : public WorldScript
{
public:
    Tier0Trainers_World() : WorldScript("Tier0Trainers_World") { }

    void OnAfterConfigLoad(bool /*reload*/) override
    {
        // SQL-only module: world updates live under data/sql/. Conf flag is informational.
        bool enabled = sConfigMgr->GetOption<bool>("Tier0Trainers.Enable", true);
        if (enabled)
            LOG_INFO("server.loading", "Tier0Trainers: module present (SQL updates via module data/sql)");
    }
};

void AddTier0TrainersScripts()
{
    new Tier0Trainers_World();
}
