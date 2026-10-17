// Export confirmed references and bounded function evidence for camera research.
// Generated assembly and decompiler output must remain in excluded local reports.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class OpenJadeCameraEntryPoints extends GhidraScript {
    public void run() throws Exception {
        if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new IllegalArgumentException("Unsupported program hash");
        if (currentProgram.getImageBase().getOffset() != 0x400000L) throw new IllegalArgumentException("Unexpected image base");
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("Expected new output directory");
        Path out = Paths.get(args[0]);
        Files.createDirectory(out);
        StringBuilder evidence = new StringBuilder();
        evidence.append("Program: ").append(currentProgram.getName()).append("\nLanguage: ")
            .append(currentProgram.getLanguageID()).append("\nImage base: ").append(currentProgram.getImageBase()).append("\n");
        long[] addresses = {8033336L,8034280L,8034372L};
        Set<Function> functions = new LinkedHashSet<>();
        for (long value : addresses) {
            Address target = toAddr(value);
            evidence.append("\nSTRING ").append(target).append("\n");
            ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(target);
            while (refs.hasNext()) {
                Reference ref=refs.next();
                Instruction ins=currentProgram.getListing().getInstructionContaining(ref.getFromAddress());
                Function fun=getFunctionContaining(ref.getFromAddress());
                evidence.append(ref.getFromAddress()).append(" ").append(ref.getReferenceType())
                    .append(" instruction=").append(ins).append(" function=")
                    .append(fun == null ? "unknown" : fun.getEntryPoint()).append("\n");
                if (fun != null) functions.add(fun);
            }
        }
        DecompInterface decompiler=new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException("Decompiler unavailable");
        try {
            for (Function fun : functions) {
                String id=fun.getEntryPoint().toString();
                StringBuilder assembly=new StringBuilder();
                InstructionIterator it=currentProgram.getListing().getInstructions(fun.getBody(),true);
                int count=0;
                while (it.hasNext() && count++<2000) {
                    Instruction ins=it.next();assembly.append(ins.getAddress()).append(" ").append(ins).append("\n");
                }
                Files.writeString(out.resolve(id+"-assembly.txt"),assembly.toString(),StandardCharsets.UTF_8);
                DecompileResults result=decompiler.decompileFunction(fun,60,monitor);
                evidence.append("\nFUNCTION ").append(id).append(" name=").append(fun.getName())
                    .append(" decompiled=").append(result.decompileCompleted()).append("\n");
                if (result.decompileCompleted()) Files.writeString(out.resolve(id+"-decompiled.c"),result.getDecompiledFunction().getC(),StandardCharsets.UTF_8);
                else evidence.append(result.getErrorMessage()).append("\n");
            }
        } finally { decompiler.dispose(); }
        Files.writeString(out.resolve("entry-points.txt"),evidence.toString(),StandardCharsets.UTF_8);
        println("OpenJade: exported " + functions.size() + " referenced functions to " + out);
    }
}

