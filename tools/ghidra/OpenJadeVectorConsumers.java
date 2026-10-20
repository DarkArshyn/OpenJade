// Inspect vector consumers and compact descriptor readers. Run with -readOnly.
// Generated assembly and decompiler output must remain in excluded local reports.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class OpenJadeVectorConsumers extends GhidraScript {
    public void run() throws Exception {
        if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new IllegalArgumentException("Unsupported program hash");
        if (currentProgram.getImageBase().getOffset() != 0x400000L) throw new IllegalArgumentException("Unexpected image base");
        String[] args = getScriptArgs();
        if (args.length < 1) throw new IllegalArgumentException("Expected new output directory and optional hexadecimal targets");
        Path out = Paths.get(args[0]);
        Files.createDirectory(out);
        StringBuilder evidence = new StringBuilder();
        evidence.append("Program: ").append(currentProgram.getName()).append("\nLanguage: ")
            .append(currentProgram.getLanguageID()).append("\nImage base: ").append(currentProgram.getImageBase()).append("\n");
        long[] addresses = {};
        if (args.length > 1) { addresses = new long[args.length-1]; for (int i=1;i<args.length;i++) addresses[i-1]=Long.parseUnsignedLong(args[i].replaceFirst("^0[xX]", ""),16); }
        Set<Function> functions = new LinkedHashSet<>();
        // Inspect only the 22-slot category table relevant to the observed token categories.
        // The initializer at 00462b10 bounds this category table to 22 entries.
        for (int category=0;category<22;category++) {
            Address slot=toAddr(0x007f46fcL+category*8L);
            long pointer=Integer.toUnsignedLong(currentProgram.getMemory().getInt(slot));
            long extra=Integer.toUnsignedLong(currentProgram.getMemory().getInt(slot.subtract(4)));
            Function handler=getFunctionAt(toAddr(pointer));
            if (handler==null && (category==15)) {
                disassemble(toAddr(pointer));
                handler=createFunction(toAddr(pointer),null);
            }
            evidence.append(String.format("SLOT %02x address=%s pointer=%08x precedingMetadata=%08x function=%s\n",category,slot,pointer,extra,handler==null?"unknown":handler.getEntryPoint().toString()));
            if (handler!=null && (category==15)) functions.add(handler);
        }
        long[] bases={0x007f47a8L,0x007f4878L,0x007f4ad0L,0x007f6f78L};
        int[] lengths={26,75,1173,27};
        for(int t=0;t<bases.length;t++) for(int n=0;n<lengths[t];n++) {
            Address record=toAddr(bases[t]+n*8L);
            int id=Short.toUnsignedInt(currentProgram.getMemory().getShort(record));
            if(!java.util.Set.of(0x965,0x96b,0x1fa5).contains(id)) continue;
            long ptr=Integer.toUnsignedLong(currentProgram.getMemory().getInt(record.add(4)));
            evidence.append(String.format("MATCH table=%08x index=%x id=%04x pointer=%08x\n",bases[t],n,id,ptr));
            if(true) {
                Function f=getFunctionAt(toAddr(ptr));
                if(f==null){disassemble(toAddr(ptr));f=createFunction(toAddr(ptr),null);}
                if(f!=null)functions.add(f);
            }
        }
        // Inspect the compact reader and object-associated triplet helper.
        for(long helper : new long[]{0x00424cc0L,0x00420660L,0x00475fb0L}) {
            Function f=getFunctionAt(toAddr(helper));
            if(f==null){disassemble(toAddr(helper));f=createFunction(toAddr(helper),null);}
            if(f!=null)functions.add(f);
        }
        for (long value : addresses) {
            Address target = toAddr(value);
            evidence.append("\nTARGET ").append(target).append("\n");
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
            int exported=0;
            for (Function fun : functions) {
                if (exported++ >= 16) { evidence.append("Function export limit reached (16).\n"); break; }
                String id=fun.getEntryPoint().toString();
                StringBuilder assembly=new StringBuilder();
                InstructionIterator it=currentProgram.getListing().getInstructions(fun.getBody(),true);
                int count=0;
                while (it.hasNext() && count++<2000) {
                    Instruction ins=it.next();assembly.append(ins.getAddress()).append(" ").append(ins).append("\n");
                }
                if (it.hasNext()) assembly.append("TRUNCATED: 2000 instruction limit\n");
                Files.writeString(out.resolve(id+"-assembly.txt"),assembly.toString(),StandardCharsets.UTF_8);
                DecompileResults result=decompiler.decompileFunction(fun,60,monitor);
                evidence.append("\nFUNCTION ").append(id).append(" name=").append(fun.getName())
                    .append(" decompiled=").append(result.decompileCompleted()).append("\n");
                if (result.decompileCompleted()) Files.writeString(out.resolve(id+"-decompiled.c"),result.getDecompiledFunction().getC(),StandardCharsets.UTF_8);
                else evidence.append(result.getErrorMessage()).append("\n");
            }
        } finally { decompiler.dispose(); }
        Files.writeString(out.resolve("references.txt"),evidence.toString(),StandardCharsets.UTF_8);
        println("OpenJade: exported " + Math.min(functions.size(),16) + " referenced functions to " + out);
    }
}















